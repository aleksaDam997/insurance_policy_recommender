import src.insurance_policy_recommender.logging.logger as logger
import src.insurance_policy_recommender.exception.exception
import sys

if __name__=='__main__':
    try:
        a = 1/0
    except Exception as e:
        raise src.insurance_policy_recommender.exception.exception.InsurancePolicyRecommenderException(str(e), sys)