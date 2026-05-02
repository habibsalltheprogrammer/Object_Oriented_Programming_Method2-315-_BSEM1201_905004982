"""
=======================================================
  PROG315 - Object-Oriented Programming 2
  Assignment: Basic API Structure with Open-Software
  Student   : Habib
  University: Limkokwing University - Sierra Leone
  Semester  : 04 | March 2026 - July 2026
=======================================================

PART A - API DESIGN (Endpoints Overview)
-----------------------------------------
ENDPOINT 1: GET  /books
  Purpose : Retrieve all books in the library
  Input   : Optional query params (title, author, category)
  Output  : List of book objects with availability status

ENDPOINT 2: GET  /books/search
  Purpose : Search books by title, author, or category
  Input   : Query string e.g. ?title=Python or ?category=Design
  Output  : Matching list of books or 404 if none found

ENDPOINT 3: POST /borrow
  Purpose : Allow a user to borrow an available book
  Input   : JSON body { "user_id": 1, "book_id": 3 }
  Output  : Success or error message with due date

ENDPOINT 4: POST /return
  Purpose : Allow a user to return a borrowed book
  Input   : JSON body { "user_id": 1, "book_id": 3 }
  Output  : Return confirmation and any overdue fine

ENDPOINT 5: GET  /overdue
  Purpose : Show all overdue books and their fines
  Input   : None
  Output  : List of overdue records with fine amounts

ENDPOINT 6: GET  /users/{user_id}/books
  Purpose : Show all books currently borrowed by a user
  Input   : user_id as path parameter (e.g. /users/2/books)
  Output  : List of borrowed books for that user
=======================================================
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


# ----------------------------------------
# APP SETUP
# ----------------------------------------

app = FastAPI(
    title="Limkokwing Library API",
    description="A simple REST API for managing the Limkokwing University Library.",
    version="1.0.0"
)


# ----------------------------------------
# BOOK DATABASE
# ----------------------------------------

books: List[Dict] = [
    {"id": 1, "title": "Python Basics",           "author": "HABIB SALL",     "category": "Programming", "available": True},
    {"id": 2, "title": "Web Design Mastery",      "author": "RUGIATU SESAY", "category": "Design",      "available": True},
    {"id": 3, "title": "Database Systems",        "author": "REGINA CLAYE",    "category": "Database",    "available": True},
    {"id": 4, "title": "ELECTRICAL Introduction", "author": "DIVINE CLAYE",  "category": "ELECTRICAL",          "available": True},
    {"id": 5, "title": "SCIENCE Fundamentals", "author": "ABNER CLAYE",  "category": "SCIENCE",  "available": True},
    {"id": 6, "title": "MINING Fundamentals", "author": "KADIJATU MEDILLA KABBA",  "category": "MINING",  "available": True},
    {"id": 7, "title": "AUDITING Fundamentals", "author": "SYLVESTER CLYE",  "category": "AUDITNG",  "available": True},
]

# user_id -> { book_id -> borrow info }
borrow_records: Dict[int, Dict[int, Dict]] = {}

# Shared lock - stops two users borrowing the same book at once
lock = asyncio.Lock()

# Fine per overdue day (Sierra Leonean Leones)
FINE_PER_DAY: int = 1000
LOAN_DAYS: int = 14


# ----------------------------------------
# REQUEST MODELS
# ----------------------------------------

class BorrowRequest(BaseModel):
    user_id: int
    book_id: int

class ReturnRequest(BaseModel):
    user_id: int
    book_id: int


# ----------------------------------------
# ASYNC - BORROW BOOK
# ----------------------------------------

async def borrow_book(user_id: int, book_id: int) -> str:
    await asyncio.sleep(1)  # simulate database delay

    async with lock:
        for book in books:
            if book["id"] == book_id:
                if not book["available"]:
                    return f"User {user_id}: Book not available"

                book["available"] = False
                borrow_date: datetime = datetime.now()
                due_date: datetime = borrow_date + timedelta(days=LOAN_DAYS)

                if user_id not in borrow_records:
                    borrow_records[user_id] = {}

                borrow_records[user_id][book_id] = {
                    "borrow_date": borrow_date,
                    "due_date": due_date
                }

                return (
                    f"User {user_id} borrowed '{book['title']}' "
                    f"— Due: {due_date.strftime('%Y-%m-%d')}"
                )

        return f"User {user_id}: Book not found"


# ----------------------------------------
# ASYNC - RETURN BOOK
# ----------------------------------------

async def return_book(user_id: int, book_id: int) -> str:
    await asyncio.sleep(1)  # simulate database delay

    async with lock:
        if user_id not in borrow_records or book_id not in borrow_records[user_id]:
            return f"User {user_id}: No borrow record found"

        record: Dict = borrow_records[user_id][book_id]
        due_date: datetime = record["due_date"]
        book_title: str = "Unknown"

        # Mark the book as available again
        for book in books:
            if book["id"] == book_id:
                book["available"] = True
                book_title = book["title"]

        # Fine calculation
        fine: int = 0
        if datetime.now() > due_date:
            fine = (datetime.now() - due_date).days * FINE_PER_DAY

        del borrow_records[user_id][book_id]

        if fine > 0:
            return f"User {user_id} returned '{book_title}' — Fine: Le {fine:,}"
        return f"User {user_id} returned '{book_title}' — No fine"


# ----------------------------------------
# REST API ENDPOINTS
# ----------------------------------------

# ENDPOINT 1 — Get all books
@app.get("/books", summary="Get all books")
async def get_all_books() -> List[Dict]:
    """
    Returns every book in the library with its availability status.

    Example response:
    [
      { "id": 1, "title": "Python Basics", "author": "Tanu Jalloh",
        "category": "Programming", "available": true }
    ]
    """
    return books


# ENDPOINT 2 — Search books
@app.get("/books/search", summary="Search books by title, author, or category")
async def search_books(
    title: Optional[str] = None,
    author: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict]:
    """
    Search the library by title, author, or category.

    Example: GET /books/search?category=Programming
    Returns all books in the Programming category.
    """
    results: List[Dict] = books

    if title:
        results = [b for b in results if title.lower() in b["title"].lower()]
    if author:
        results = [b for b in results if author.lower() in b["author"].lower()]
    if category:
        results = [b for b in results if category.lower() in b["category"].lower()]

    if not results:
        raise HTTPException(status_code=404, detail="No books found matching your search.")

    return results


# ENDPOINT 3 — Borrow a book
@app.post("/borrow", summary="Borrow a book")
async def borrow(request: BorrowRequest) -> Dict:
    """
    Borrow a book from the library.

    Example request body:
    { "user_id": 2, "book_id": 3 }

    Example success response:
    { "message": "User 2 borrowed 'Database Systems' — Due: 2026-05-12" }
    """
    result: str = await borrow_book(request.user_id, request.book_id)

    if "not available" in result or "not found" in result:
        raise HTTPException(status_code=400, detail=result)

    return {"message": result}


# ENDPOINT 4 — Return a book
@app.post("/return", summary="Return a borrowed book")
async def return_borrowed(request: ReturnRequest) -> Dict:
    """
    Return a book that was previously borrowed.

    Example request body:
    { "user_id": 2, "book_id": 3 }

    Example success response:
    { "message": "User 2 returned 'Database Systems' — No fine" }
    """
    result: str = await return_book(request.user_id, request.book_id)

    if "No borrow record found" in result:
        raise HTTPException(status_code=404, detail=result)

    return {"message": result}


# ENDPOINT 5 — Get all overdue books
@app.get("/overdue", summary="Get all overdue books and fines")
async def get_overdue() -> List[Dict]:
    """
    Returns a list of all books that are past their due date,
    showing the user, book title, days overdue, and fine amount.

    Example response:
    [
      { "user_id": 1, "book_title": "Python Basics",
        "days_overdue": 3, "fine_sll": 3000 }
    ]
    """
    overdue_list: List[Dict] = []

    for user_id, user_books in borrow_records.items():
        for book_id, record in user_books.items():
            if datetime.now() > record["due_date"]:
                days_late: int = (datetime.now() - record["due_date"]).days
                fine: int = days_late * FINE_PER_DAY

                for book in books:
                    if book["id"] == book_id:
                        overdue_list.append({
                            "user_id": user_id,
                            "book_id": book_id,
                            "book_title": book["title"],
                            "days_overdue": days_late,
                            "fine_sll": fine
                        })

    return overdue_list


# ENDPOINT 6 — Get a user's borrowed books
@app.get("/users/{user_id}/books", summary="Get books borrowed by a specific user")
async def get_user_books(user_id: int) -> List[Dict]:
    """
    Returns all books currently borrowed by a specific user.

    Example: GET /users/2/books

    Example response:
    [
      { "book_id": 3, "book_title": "Database Systems",
        "due_date": "2026-05-12", "is_overdue": false }
    ]
    """
    if user_id not in borrow_records or not borrow_records[user_id]:
        return []

    result: List[Dict] = []
    for book_id, record in borrow_records[user_id].items():
        for book in books:
            if book["id"] == book_id:
                result.append({
                    "book_id": book_id,
                    "book_title": book["title"],
                    "due_date": record["due_date"].strftime("%Y-%m-%d"),
                    "is_overdue": datetime.now() > record["due_date"]
                })

    return result


# ----------------------------------------
# MAIN - Concurrent Test (Part B Demo)
# ----------------------------------------

async def main() -> None:
    print("\n--- BORROWING (MULTIPLE USERS AT SAME TIME) ---")

    # Three users borrow at the same time using asyncio.gather
    results = await asyncio.gather(
        borrow_book(1, 1),   # User 1 borrows Book 1  -> success
        borrow_book(2, 1),   # User 2 borrows Book 1  -> fails (same book)
        borrow_book(3, 2)    # User 3 borrows Book 2  -> success
    )
    for r in results:
        print(r)

    print("\n--- RETURN & RE-BORROW ---")

    results2 = await asyncio.gather(
        return_book(1, 1),   # User 1 returns Book 1
        borrow_book(4, 1)    # User 4 borrows Book 1 at same time
    )
    for r in results2:
        print(r)


# RUN PROGRAM
if __name__ == "__main__":
    asyncio.run(main())

    print("\n--- Starting REST API Server ---")
    print("Interactive Docs -> http://127.0.0.1:8000/docs")
    uvicorn.run("library_system:app", host="127.0.0.1", port=8000, reload=True)
