class AbbotStudyError(Exception):
    def __init__(self, message: str, code: str = "abbot_study_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)
