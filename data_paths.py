"""农场默认目录与旧预览目录的无覆盖迁移。"""

from pathlib import Path


def data_directories(base, configured=None):
    if configured is not None:
        return Path(configured), None
    return Path(base) / 'farm_db', Path(base) / 'farm_preview'


def prepare_directory(target, legacy=None):
    target = Path(target).absolute()
    if legacy is not None:
        legacy = Path(legacy).absolute()
        if (target.name != 'farm_db' or legacy.name != 'farm_preview'
                or target.parent.resolve() != legacy.parent.resolve()):
            raise ValueError('Farm migration requires default sibling paths')
        if target.is_symlink() or legacy.is_symlink():
            raise ValueError('Farm migration does not follow directory links')
        if (legacy / 'farm-preview.sqlite3').is_file():
            if target.exists():
                raise FileExistsError(
                    'farm_db already exists beside farm_preview; '
                    'select farm_preview_data_dir explicitly before startup'
                )
            legacy.rename(target)
            return True
    target.mkdir(parents=True, exist_ok=True)
    return False
