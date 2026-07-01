import inspect
import warnings


def apply_runtime_patches() -> None:
    if not hasattr(inspect, 'getargspec'):
        inspect.getargspec = inspect.getfullargspec

    warnings.filterwarnings(
        'ignore',
        message='pkg_resources is deprecated as an API.*',
        category=UserWarning,
    )
