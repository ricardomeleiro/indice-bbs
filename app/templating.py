from fastapi.templating import Jinja2Templates

from models import Role, ROLE_LABELS
from services.kpi import MONTH_LABELS_PT, MONTH_FULL_PT

templates = Jinja2Templates(directory="templates")

# Map both Enum and string keys to ensure lookup never fails
role_labels_safe = {**ROLE_LABELS, **{r.value: label for r, label in ROLE_LABELS.items()}}

templates.env.globals.update({
    "MONTH_LABELS_PT": MONTH_LABELS_PT,
    "MONTH_FULL_PT": MONTH_FULL_PT,
    "ROLE_LABELS": role_labels_safe,
    "Role": Role,
})
