"""
FSM состояния для многошаговых процессов
"""
from telegram.ext import ConversationHandler
from enum import Enum


# Состояния для сбора информации об НКО
class NKOSetupStates(Enum):
    """Состояния процесса настройки профиля НКО"""
    WAITING_ORG_NAME = "waiting_org_name"
    WAITING_DESCRIPTION = "waiting_description"
    WAITING_ACTIVITY_TYPES = "waiting_activity_types"
    WAITING_TARGET_AUDIENCE = "waiting_target_audience"
    WAITING_TONE_OF_VOICE = "waiting_tone_of_voice"
    WAITING_CONTACT_INFO = "waiting_contact_info"
    WAITING_BRAND_COLORS = "waiting_brand_colors"


# Состояния для структурированной генерации текста
class StructuredTextStates(Enum):
    """Состояния процесса структурированной генерации текста"""
    WAITING_EVENT_TYPE = "waiting_event_type"
    WAITING_EVENT_NAME = "waiting_event_name"
    WAITING_EVENT_DATE = "waiting_event_date"
    WAITING_EVENT_PLACE = "waiting_event_place"
    WAITING_PARTICIPANTS = "waiting_participants"
    WAITING_DETAILS = "waiting_details"
    WAITING_STYLE = "waiting_style"
    WAITING_CTA = "waiting_cta"


# Состояния для генерации изображений
class ImageGenerationStates(Enum):
    """Состояния процесса генерации изображений"""
    WAITING_DESCRIPTION = "waiting_image_description"
    WAITING_REFERENCE = "waiting_reference"
    WAITING_STYLE = "waiting_image_style"
    WAITING_ASPECT_RATIO = "waiting_aspect_ratio"


# Состояния для контент-плана
class ContentPlanStates(Enum):
    """Состояния процесса создания контент-плана"""
    WAITING_PERIOD = "waiting_plan_period"
    WAITING_FREQUENCY = "waiting_plan_frequency"
    WAITING_DAYS = "waiting_plan_days"
    WAITING_TIME = "waiting_plan_time"
    WAITING_TOPICS = "waiting_plan_topics"


# Состояния для генерации на основе примеров
class ExamplesTextStates(Enum):
    """Состояния процесса генерации текста на основе примеров"""
    WAITING_EXAMPLES = "waiting_examples"
    WAITING_PROMPT = "waiting_examples_prompt"
    WAITING_STYLE_ANALYSIS = "waiting_style_analysis"


# Константы для ConversationHandler
END = ConversationHandler.END
CANCEL = "cancel"

# Числовые константы для использования в ConversationHandler
NKO_SETUP = {
    "org_name": 1,
    "description": 2,
    "activity_types": 3,
    "target_audience": 4,
    "tone_of_voice": 5,
    "contact_info": 6,
    "brand_colors": 7
}

STRUCTURED_TEXT = {
    "event_type": 10,
    "event_name": 11,
    "event_date": 12,
    "event_place": 13,
    "participants": 14,
    "details": 15,
    "style": 16,
    "cta": 17
}

IMAGE_GENERATION = {
    "description": 20,
    "reference": 21,
    "style": 22,
    "aspect_ratio": 23
}

CONTENT_PLAN = {
    "period": 30,
    "frequency": 31,
    "days": 32,
    "time": 33,
    "topics": 34
}

EXAMPLES_TEXT = {
    "examples": 40,
    "prompt": 41,
    "style_analysis": 42
}

