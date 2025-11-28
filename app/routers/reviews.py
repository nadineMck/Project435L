from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, models
from ..deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=schemas.ReviewOut)
def create_review(
    review_in: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    room = db.query(models.Room).filter(models.Room.id == review_in.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    review = models.Review(
        user_id=current_user.id,
        room_id=review_in.room_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/room/{room_id}", response_model=List[schemas.ReviewOut])
def get_reviews_for_room(room_id: int, db: Session = Depends(get_db)):
    # Only return non-deleted reviews to normal consumers
    return (
        db.query(models.Review)
        .filter(models.Review.room_id == room_id, models.Review.deleted == False)
        .all()
    )


@router.patch("/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    review_id: int,
    review_update: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.deleted:
        raise HTTPException(status_code=400, detail="Cannot update a deleted review")

    # Regular/facility_manager: only own reviews; admin: any review
    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to update this review")

    data = review_update.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Regular/facility_manager: delete own reviews.
    Admin: "remove" any review (soft delete).
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to delete this review")

    review.deleted = True
    db.commit()
    return {"detail": "Review removed"}


@router.post("/{review_id}/restore")
def restore_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: restore a previously deleted review.
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.deleted = False
    db.commit()
    return {"detail": "Review restored"}


@router.post("/{review_id}/flag")
def flag_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: mark a review as flagged (moderation).
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.flagged = True
    db.commit()
    return {"detail": "Review flagged"}


@router.post("/{review_id}/unflag")
def unflag_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: clear the flagged status of a review.
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.flagged = False
    db.commit()
    return {"detail": "Review unflagged"}
