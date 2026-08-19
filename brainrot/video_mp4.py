import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager

from django.conf import settings
from django.core.files import File


class Mp4TranscodeError(RuntimeError):
    pass


def _ffmpeg_binary():
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise Mp4TranscodeError('Video conversion is temporarily unavailable (ffmpeg missing).')
    return ffmpeg


def _transcode(source_path, output_path):
    command = [
        _ffmpeg_binary(),
        '-hide_banner',
        '-loglevel', 'error',
        '-y',
        '-i', source_path,
        '-map', '0:v:0',
        '-map', '0:a:0?',
        '-sn',
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-profile:v', 'baseline',
        '-level', '3.1',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        '-map_metadata', '-1',
        output_path,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise Mp4TranscodeError('Preparing the MP4 took too long.') from exc

    if completed.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
        detail = (completed.stderr or '').strip().splitlines()
        detail = detail[-1] if detail else 'ffmpeg did not produce an MP4 file'
        raise Mp4TranscodeError(f'Could not prepare the MP4: {detail}')


@contextmanager
def transcode_upload_to_mp4(upload):
    """Yield a Django File containing one canonical H.264/AAC MP4.

    The uploaded source is copied to a temporary file because MediaRecorder
    uploads may be in-memory files. Both temporary files are removed when the
    context exits; callers must save the yielded file before then.
    """
    os.makedirs(settings.PRIVATE_MEDIA_ROOT, exist_ok=True)
    source = tempfile.NamedTemporaryFile(
        suffix=os.path.splitext(upload.name or '')[1] or '.video',
        prefix='hof-source-',
        dir=settings.PRIVATE_MEDIA_ROOT,
        delete=False,
    )
    source_path = source.name
    output = tempfile.NamedTemporaryFile(
        suffix='.mp4',
        prefix='hof-mp4-',
        dir=settings.PRIVATE_MEDIA_ROOT,
        delete=False,
    )
    output_path = output.name
    output.close()

    try:
        for chunk in upload.chunks():
            source.write(chunk)
        source.close()
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass

        _transcode(source_path, output_path)
        handle = open(output_path, 'rb')
        try:
            yield File(handle, name='recording.mp4')
        finally:
            handle.close()
    finally:
        try:
            source.close()
        except OSError:
            pass
        for path in (source_path, output_path):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass


@contextmanager
def transcode_path_to_mp4(source_path):
    """Yield the path of a temporary canonical MP4 converted from source_path."""
    os.makedirs(settings.PRIVATE_MEDIA_ROOT, exist_ok=True)
    output = tempfile.NamedTemporaryFile(
        suffix='.mp4',
        prefix='hof-backfill-',
        dir=settings.PRIVATE_MEDIA_ROOT,
        delete=False,
    )
    output_path = output.name
    output.close()
    try:
        _transcode(source_path, output_path)
        yield output_path
    finally:
        try:
            os.unlink(output_path)
        except FileNotFoundError:
            pass
