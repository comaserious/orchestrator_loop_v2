import logging 

logger = logging.getLogger(__name__)

class HumanInputRequired(Exception):
    """툴 실행 중 사람의 선택이 필요할 때 발생시키는 예외."""

    def __init__(self, question: str, options: list[str]):
        self.question = question
        self.options  = options
        super().__init__(question)
        logger.info(f"HumanInputRequired: {question}, {options}")
