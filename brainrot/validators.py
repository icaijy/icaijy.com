import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class ValidatedVideo:
    mime_type: str
    extension: str
    duration_seconds: float


def _packet_duration(path, ffprobe):
    """Fallback for MediaRecorder WebM files that omit container duration."""
    completed = subprocess.run(
        [
            ffprobe, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'packet=pts_time,duration_time',
            '-of', 'csv=p=0', path,
        ],
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    if completed.returncode != 0:
        return 0
    first_pts = None
    end_time = None
    for line in completed.stdout.splitlines():
        values = line.split(',')
        try:
            pts = float(values[0])
            packet_duration = float(values[1]) if len(values) > 1 and values[1] else 0
            first_pts = pts if first_pts is None else min(first_pts, pts)
            packet_end = pts + packet_duration
            end_time = packet_end if end_time is None else max(end_time, packet_end)
        except ValueError:
            continue
    if first_pts is None or end_time is None:
        return 0
    # MediaRecorder packets may retain timestamps from the long-lived camera
    # stream. Duration is the packet span, not the final absolute PTS.
    return max(0, end_time - first_pts)


def _sniff_container(upload):
    upload.seek(0)
    header = upload.read(32)
    upload.seek(0)

    if header.startswith(b'\x1aE\xdf\xa3'):
        return 'video/webm', 'webm'
    if len(header) >= 12 and header[4:8] == b'ftyp':
        return 'video/mp4', 'mp4'
    raise ValidationError('Only genuine WebM or MP4 video files are accepted.')


def _probe_video(upload, expected_mime):
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        raise ValidationError('Video verification is temporarily unavailable (ffprobe missing).')

    suffix = '.webm' if expected_mime == 'video/webm' else '.mp4'
    temporary_path = None
    try:
        if hasattr(upload, 'temporary_file_path'):
            path = upload.temporary_file_path()
        else:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                for chunk in upload.chunks():
                    temporary.write(chunk)
                temporary_path = temporary.name
                path = temporary_path
            upload.seek(0)

        completed = subprocess.run(
            [
                ffprobe, '-v', 'error', '-show_entries',
                'format=duration:stream=codec_type,codec_name',
                '-of', 'json', path,
            ],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if completed.returncode != 0:
            raise ValidationError('The uploaded file is not a readable video.')

        payload = json.loads(completed.stdout)
        streams = payload.get('streams', [])
        video_streams = [stream for stream in streams if stream.get('codec_type') == 'video']
        if not video_streams:
            raise ValidationError('The upload does not contain a video stream.')
        allowed_codecs = {'vp8', 'vp9', 'h264', 'av1'}
        if not any(stream.get('codec_name') in allowed_codecs for stream in video_streams):
            raise ValidationError('The video codec is not supported.')
        try:
            container_duration = float(payload.get('format', {}).get('duration', 0))
        except (TypeError, ValueError):
            container_duration = 0

        # MediaRecorder may write a non-zero container duration based on the
        # lifetime of the camera track rather than this recording. Packet PTS
        # span reflects the actual encoded evidence and is therefore preferred
        # whenever ffprobe can recover it.
        packet_duration = _packet_duration(path, ffprobe)
        duration = packet_duration if packet_duration > 1 else container_duration
        if duration <= 1 or duration > settings.HOF_MAX_VIDEO_SECONDS:
            raise ValidationError(
                f'Video duration must be between 1 and {settings.HOF_MAX_VIDEO_SECONDS:g} seconds.'
            )
        return duration
    except (json.JSONDecodeError, ValueError, subprocess.TimeoutExpired):
        raise ValidationError('The uploaded video could not be safely inspected.')
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def validate_hall_of_fame_video(upload):
    if upload.size <= 0 or upload.size > settings.HOF_MAX_UPLOAD_BYTES:
        max_mb = settings.HOF_MAX_UPLOAD_BYTES / (1024 * 1024)
        raise ValidationError(f'Video must be no larger than {max_mb:g} MB.')

    mime_type, extension = _sniff_container(upload)
    supplied_type = (upload.content_type or '').split(';', 1)[0].lower()
    compatible_types = {
        'video/webm': {'video/webm', 'application/octet-stream'},
        'video/mp4': {'video/mp4', 'application/mp4', 'application/octet-stream'},
    }
    if supplied_type not in compatible_types[mime_type]:
        raise ValidationError('The declared MIME type does not match the video container.')

    duration = _probe_video(upload, mime_type)
    upload.seek(0)
    return ValidatedVideo(mime_type, extension, duration)
