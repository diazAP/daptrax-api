from pydantic import BaseModel


class BackupImportError(BaseModel):
    row: int
    message: str


class BackupImportResult(BaseModel):
    total_rows: int
    success_rows: int
    failed_rows: int
    errors: list[BackupImportError]