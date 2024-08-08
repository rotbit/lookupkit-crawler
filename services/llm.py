import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from services.llm_moonshot import LLMMoonshot


def get_llm_model(model_name: str):
    if "moonshot" in model_name:
        return LLMMoonshot(model_name)
    
    return LLMMoonshot(model_name)