import os
import shutil
import subprocess
import tempfile

from django.conf import settings


class Mp4TranscodeError(RuntimeError):
    pass


def open_compatible_mp4(entry):
    """Return (open file handle, size) for a short, broadly playable MP4.

    HOF recordings may be stored as WebM because that is what MediaRecorder
    produced on the submitting browser. Downloads are normalised server-side so
    Safari/iPhone users do not need WebCodecs or a client-side transcoder.

    The temporary file is unlinked immediately after opening on the Linux
    production host; FileResponse keeps the descriptor alive until streaming
    finishes, so the conversion does not build a permanent second video archive.
    """
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise Mp4TranscodeError('MP4 download is temporarily unavailable (ffmpeg missing).')

    try:
        source_path = entry.video.path
    except (NotImplementedError, AttributeError) as exc:
        raise Mp4TranscodeError('The recording storage cannot be transcoded on this server.') from exc

    os.makedirs(settings.PRIVATE_MEDIA_ROOT, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        suffix='.mp4',
        prefix=f'hof-{entry.pk}-',
        dir=settings.PRIVATE_MEDIA_ROOT,
        delete=False,
    )
    output_path = temporary.name
    temporary.close()

    command = [
        ffmpeg,
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
        if completed.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            detail = (completed.stderr or '').strip().splitlines()
            detail = detail[-1] if detail else 'ffmpeg did not produce an MP4 file'
            raise Mp4TranscodeError(f'Could not prepare the MP4 download: {detail}')

        size = os.path.getsize(output_path)
        handle = open(output_path, 'rb')
        # Production runs on Linux. An unlinked open file remains readable by
        # FileResponse but disappears automatically when the descriptor closes.
        try:
            os.unlink(output_path)
        except OSError:
            # Harmless fallback for non-POSIX development environments.
            pass
        return handle, size
    except subprocess.TimeoutExpired as exc:
        raise Mp4TranscodeError('Preparing the MP4 download took too long.') from exc
    except Exception:
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except OSError:
                pass
        raise
