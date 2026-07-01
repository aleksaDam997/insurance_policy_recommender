import sys 
from src.insurance_policy_recommender.logging import logger

class InsurancePolicyRecommenderException(Exception):
    def __init__(self, error_message: str, error_details=sys):
        super().__init__(error_message)

        _, _, exc_tb = error_details.exc_info()

        self.error_message = error_message

        if exc_tb:
            self.line_no = exc_tb.tb_lineno
            self.file_name = exc_tb.tb_frame.f_code.co_filename
        else:
            self.line_no = None
            self.file_name = None

    def __str__(self):
        return (
            f"Error occurred in script [{self.file_name}] "
            f"at line [{self.line_no}] : {self.error_message}"
        )


if __name__=='__main__':
    try:
        logger.logging.info('This is a test log message.')
        a = 1/0
    except Exception as e:
        raise InsurancePolicyRecommenderException(str(e), sys)