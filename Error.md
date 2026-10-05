# ⚠️ Incident Report: `AttributeError: 'AsyncSession' object has no attribute 'query'`

---

## 1. Issue Summary

When calling the user registration endpoint (`POST /api/v1/auth/register`), Uvicorn terminated request execution with a `500 Internal Server Error` and logged the following exception:

```python
File "C:\Users\skfir\Desktop\Project-1\backend\app\api\v1\auth_register.py", line 54, in register_user
  existing_user = db.query(User).filter_by(email=normalized_email).first()
AttributeError: 'AsyncSession' object has no attribute 'query'
```

---

## 2. Root Cause Analysis

### The Mismatch Between Session Type and Query Syntax
There is an architectural type mismatch between the **database session provider** and the **route handlers**:

1. **In `backend/app/core/database.py`**:
   The `get_db` dependency was configured to create and yield an **`AsyncSession`**:
   ```python
   AsyncSessionLocal = async_sessionmaker(
       bind=engine,
       class_=AsyncSession,  # <--- Asynchronous Session
       ...
   )

   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       async with AsyncSessionLocal() as session:
           yield session
   ```

2. **In `backend/app/api/v1/auth_register.py` (and other route handlers)**:
   The endpoint function is declared as synchronous (`def`, not `async def`), accepting a synchronous `db: Session`, and invoking the legacy/ORM query builder:
   ```python
   @router.post("/register", status_code=status.HTTP_201_CREATED)
   def register_user(
       request: RegisterRequest,
       background_tasks: BackgroundTasks,
       db: Session = Depends(get_db),
   ):
       # Calling .query() on an AsyncSession raises AttributeError!
       existing_user = db.query(User).filter_by(email=normalized_email).first()
   ```

3. **Why It Breaks**:
   In SQLAlchemy, `AsyncSession` **does not have a `.query()` attribute**. 
   - Synchronous `Session` uses: `db.query(Model).filter(...)`
   - Asynchronous `AsyncSession` uses: `await db.execute(select(Model).filter(...))`

When FastAPI passes an `AsyncSession` into a route that calls `db.query()`, Python immediately throws `AttributeError: 'AsyncSession' object has no attribute 'query'`.

---

## 3. Solutions

There are two valid approaches to resolve this issue:

---

### Option A: Standard Synchronous Engine & Session (Recommended & Fastest Fix)

Since all current route controllers (`auth_register.py`, `auth_login.py`, `routes_feed.py`, `routes_search.py`, `routes_bookmarks.py`, `routes_reads.py`, `routes_share.py`) are written using standard synchronous `db.query(...)`, configuring a synchronous `SessionLocal` in `database.py` resolves the issue immediately across all 7 routers without breaking any existing code.

#### Implementation in `backend/app/core/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from typing import Generator
from app.core.config import get_settings

class Base(DeclarativeBase):
    pass

settings = get_settings()

# Convert async driver string to standard sync driver if needed
# e.g., postgresql+asyncpg:// -> postgresql+psycopg:// (or postgresql://)
# e.g., sqlite+aiosqlite:// -> sqlite:///
db_url = settings.DATABASE_URL
if "sqlite+aiosqlite://" in db_url:
    db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")
elif "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

engine = create_engine(
    db_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db() -> Generator[Session, None, None]:
    """
    Yields a scoped synchronous Session compatible with db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Option B: Full Async Migration (SQLAlchemy 2.0 2.0 `select()` Syntax)

If you strictly want end-to-end `async`/`await` across all database calls, every route and dependency must be refactored to use `async def` and SQLAlchemy 2.0's `select()` statement.

#### Example Refactor for `auth_register.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),  # <-- Use AsyncSession
) -> Dict[str, Any]:
    ...
    # Replace db.query(User).filter_by(...) with select(User):
    stmt = select(User).where(User.email == normalized_email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User(...)
    db.add(user)
    await db.commit()  # <-- Must await commit
    ...
```

*Note: Option B requires refactoring all query statements across all 7 route files.*

---

## 4. Summary Table

| Approach | Changes Required | Compatibility | Implementation Effort |
|---|---|---|---|
| **Option A (Sync Session)** | Modify `backend/app/core/database.py` only | 100% compatible with existing `db.query(...)` across all 7 routers | 2 minutes |
| **Option B (Full Async)** | Refactor `auth_register.py`, `auth_login.py`, `routes_*.py`, `deps.py` | Requires changing all queries to `await db.execute(select(...))` | 1-2 hours |

---
---

# ⚠️ Incident Report #2: `Uncaught TypeError: articles is not iterable at ArticleGrid`

---

## 1. Issue Summary

When loading the main news dashboard (`http://localhost:5173/`), React threw a client-side runtime exception caught by `SwissErrorBoundary`:

```text
Uncaught TypeError: articles is not iterable
    at ArticleGrid (ArticleGrid.jsx:53:44)
    at DashboardPage (DashboardPage.jsx:93:33)
```

---

## 2. Root Cause Analysis

### API Response Structure vs. Frontend Unpacking
1. **Backend Payload Contract**:
   The FastAPI backend endpoints (`/api/v1/news/feed`, `/api/v1/news/search`, `/api/v1/news/bookmarks`) return paginated response models (`FeedResponse`, `SearchResponse`, `BookmarkListResponse`) structured as:
   ```json
   {
     "items": [ /* article objects */ ],
     "total": 30,
     "page": 1,
     "page_size": 10,
     "total_pages": 3
   }
   ```

2. **Frontend Expectation**:
   In `frontend/src/pages/DashboardPage.jsx` and `frontend/src/hooks/useNewsFeed.js`, the code was attempting to read `.articles`:
   ```javascript
   const fetchedArticles = data?.articles || data || [];
   ```
   Because `data.articles` was `undefined`, JavaScript evaluated the fallback `data || []`, which evaluated to the **Object** `data` (`{ items: [...], total: ... }`).

3. **Component Crash in `<ArticleGrid />`**:
   Passing this Object as the `articles` prop to `<ArticleGrid articles={articles} />` caused:
   ```javascript
   const [leadStory, ...secondaryStories] = articles; // ❌ TypeError: articles is not iterable
   ```

---

## 3. Solution & Fix Applied

### 1. Robust Array Extraction in `DashboardPage.jsx`
Updated `fetchFeed`, `fetchBookmarks`, `handleSearch`, and `handleLoadMore` to prioritize `data?.items`:
```javascript
// Feed
const fetchedArticles = data?.items || data?.articles || (Array.isArray(data) ? data : []);

// Bookmarks
setBookmarks(data?.items || data?.bookmarks || (Array.isArray(data) ? data : []));

// Search
const results = data?.items || data?.articles || (Array.isArray(data) ? data : []);

// Load More
const moreArticles = data?.items || data?.articles || (Array.isArray(data) ? data : []);
```

### 2. Matching Support in Hook `useNewsFeed.js`
Updated `executeQuery` and `loadMore` to extract from `data?.items || data?.articles || []`.

### 3. Component Defensive Guard in `ArticleGrid.jsx`
Added defense-in-depth inside `ArticleGrid` so non-array inputs never crash the render tree:
```javascript
const safeArticles = Array.isArray(articles) ? articles : (articles?.items || []);
```

