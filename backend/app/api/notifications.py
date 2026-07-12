from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.notifications import list_notifications, notification_to_response
from app.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def get_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = list_notifications(db, user=user)
    return [notification_to_response(item) for item in notifications]
