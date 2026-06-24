class PersonalColorServiceError(Exception):
    status_code = 500
    code = "analysis_failed"
    default_message = "분석 중 오류가 발생했습니다."

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.code
        super().__init__(self.message)


class InvalidImageError(PersonalColorServiceError):
    status_code = 400
    code = "invalid_image"
    default_message = "이미지 파일을 확인할 수 없습니다."


class FaceNotDetectedError(PersonalColorServiceError):
    status_code = 400
    code = "face_not_detected"
    default_message = "얼굴을 찾을 수 없습니다."


class AnalysisProviderUnavailableError(PersonalColorServiceError):
    status_code = 503
    code = "analysis_provider_unavailable"
    default_message = "AI 분석 서비스를 사용할 수 없습니다."


class AnalysisFailedError(PersonalColorServiceError):
    status_code = 500
    code = "analysis_failed"
    default_message = "분석 중 오류가 발생했습니다."

