from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
import models
from models import User, ContactMessage, MediaItem, SharedMedia
from typing import Optional
from auth_utils import hash_password, verify_password, get_current_user_or_none, get_current_user
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile
import os
from pathlib import Path
import time

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# STATIC FILES
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = Path("static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[User] = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("Snapi.html", {"request": request, "user": user})


@app.get("/add-photos-videos", response_class=HTMLResponse)
async def add_media(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_or_none),
        db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(
            url="/login?next_url=/add-photos-videos",
            status_code=status.HTTP_302_FOUND
        )

    # User's own media
    user_media = db.query(MediaItem).filter(MediaItem.user_id == current_user.id).order_by(
        MediaItem.upload_date.desc()).all()

    # Media shared with the current user
    shared_items = (
        db.query(MediaItem)
        .join(SharedMedia, SharedMedia.media_id == MediaItem.id)
        .filter(SharedMedia.shared_with_id == current_user.id)
        .all()
    )

    context = {
        "request": request,
        "user": current_user,
        "user_media": user_media,
        "shared_media": shared_items,
        "message": request.query_params.get("message")
    }

    return templates.TemplateResponse("add-photos-videos.html", context)


@app.post("/upload-media")
async def upload_media(
        request: Request,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    unique_filename = f"{current_user.id}_{int(time.time())}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save file.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
        file_type = 'image'
    elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
        file_type = 'video'
    else:
        file_type = 'other'

    new_media = MediaItem(
        user_id=current_user.id,
        filename=unique_filename,
        file_path=str(file_path).replace("\\", "/"),
        file_type=file_type
    )
    db.add(new_media)
    db.commit()
    db.refresh(new_media)

    return RedirectResponse(
        url="/add-photos-videos?message=Media uploaded successfully!",
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/delete-media/{media_id}")
def delete_media(
        media_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()

    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found.")

    if media_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this media item.")

    try:
        file_path = Path(media_item.file_path)
        if file_path.exists():
            os.remove(file_path)
    except Exception as e:
        print(f"Warning: Could not delete file {media_item.file_path}. Error: {e}")

    db.delete(media_item)
    db.commit()

    return RedirectResponse(
        url="/add-photos-videos?message=Media item deleted successfully!",
        status_code=status.HTTP_303_SEE_OTHER
    )


# Share media route
@app.post("/share-media")
def share_media(
        media_id: int = Form(...),
        share_with_username: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    media = db.query(MediaItem).filter(MediaItem.id == media_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")

    if media.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot share media you don't own.")

    share_user = db.query(User).filter(User.username == share_with_username).first()

    if not share_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check if already shared
    existing_share = db.query(SharedMedia).filter(
        SharedMedia.media_id == media.id,
        SharedMedia.shared_with_id == share_user.id
    ).first()

    if existing_share:
        return RedirectResponse(
            url=f"/add-photos-videos?message=Already shared with {share_with_username}",
            status_code=303
        )

    shared = SharedMedia(
        media_id=media.id,
        owner_id=current_user.id,
        shared_with_id=share_user.id
    )
    db.add(shared)
    db.commit()

    return RedirectResponse(
        url=f"/add-photos-videos?message=Shared successfully with {share_with_username}",
        status_code=303
    )


# --- THE REST OF YOUR ROUTES BELOW (unchanged) ---

@app.get("/about-us", response_class=HTMLResponse)
async def about_us(request: Request, user: Optional[User] = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("about-us.html", {"request": request, "user": user})


@app.get("/contact-us", response_class=HTMLResponse)
async def contact_us(request: Request, user: Optional[User] = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("contact-us.html", {"request": request, "user": user})


@app.post("/contact-us", response_class=HTMLResponse)
def post_contact_us(
        request: Request,
        name: str = Form(...),
        email: str = Form(...),
        subject: str = Form(...),
        message: str = Form(...),
        db: Session = Depends(get_db),
        user: Optional[User] = Depends(get_current_user_or_none)
):
    new_message = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=message
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    context = {
        "request": request,
        "user": user,
        "success": True,
        "submitted_name": name,
        "submitted_email": email,
        "submitted_subject": subject,
        "submitted_message": message
    }
    return templates.TemplateResponse("contact-us.html", context)


@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request, user: Optional[User] = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("signup.html", {"request": request, "user": user})


@app.post("/signup")
def signup(
        request: Request,
        email: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("signup.html",
                                          {"request": request, "user": None, "error": "Username already taken."})

    hashed_password = hash_password(password)
    new_user = User(email=email, username=username, hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request, next_url: str = None, user: Optional[User] = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("login.html", {"request": request, "next_url": next_url or "/", "user": user})


@app.post("/login")
def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next_url: str = Form("/"),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if user and verify_password(password, user.hashed_password):
        response = RedirectResponse(url=next_url, status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=str(user.id), httponly=True, path='/')
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password.",
            "next_url": next_url,
            "user": None
        })


@app.get("/logout")
def logout_user():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


@app.get("/settings", response_class=HTMLResponse)
async def get_user_settings(request: Request, current_user: User = Depends(get_current_user)):
    context = {"request": request, "user": current_user}
    return templates.TemplateResponse("settings.html", context)


@app.post("/change-password")
def change_password(
        request: Request,
        old_password: str = Form(...),
        new_password: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not verify_password(old_password, current_user.hashed_password):
        return RedirectResponse(
            url="/settings?error=Invalid old password",
            status_code=status.HTTP_303_SEE_OTHER
        )

    current_user.hashed_password = hash_password(new_password)
    db.commit()

    return RedirectResponse(
        url="/settings?message=Password changed successfully!",
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/delete-account")
def delete_account(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db.delete(current_user)
    db.commit()

    response = RedirectResponse(
        url="/?message=Account deleted successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )

    response.delete_cookie(key="access_token")
    return response

