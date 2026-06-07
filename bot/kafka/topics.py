# Bot → Backend (producer)
FILES_UPLOADED      = "files.uploaded"
TOPIC_FILES_UPLOADED = FILES_UPLOADED
TOPIC_MESSAGES_RAW   = "messages.raw"
TOPIC_AUDIO_UPLOAD   = "audio.upload"
TOPIC_TASK_CONFIRMED = "tasks.confirmed"
TOPIC_TASK_REJECTED  = "tasks.rejected"
TOPIC_STATUS_CHANGED = "tasks.status"

# Backend → Bot (consumer)
TOPIC_TASKS_STATE        = "tasks.state"
TOPIC_BOTS_TASKS         = "bots.tasks"
TOPIC_BOTS_NOTIFICATIONS = "bots.notifications"

# Courses
TOPIC_COURSES_INDEXED           = "courses.indexed"
TOPIC_COURSES_RECOMMEND_REQUEST = "courses.recommend.request"
TOPIC_COURSES_RECOMMEND_RESULT  = "courses.recommend.result"


class Topics:
    FILES_UPLOADED = FILES_UPLOADED
