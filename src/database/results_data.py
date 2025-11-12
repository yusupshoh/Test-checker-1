from sqlalchemy import Column, BigInteger, String, Integer, select, func, DateTime, desc, asc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple
from src.database.sign_data import User

from src.database.base import Base

class Result(Base):
    __tablename__ = 'results'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    test_id = Column(BigInteger, nullable=False, index=True)
    correct_count = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    user_answers_key = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<Result(test_id={self.test_id}, user_id={self.user_id}, result={self.correct_count}/{self.total_questions})>"

async def add_new_result(
    session: AsyncSession,
    user_id: int,
    test_id: str,
    correct_count: int,
    total_questions: int,
    user_answers_key: str
) -> Result:

    new_result = Result(
        user_id=user_id,
        test_id=test_id,
        correct_count=correct_count,
        total_questions=total_questions,
        user_answers_key=user_answers_key
    )
    session.add(new_result)
    await session.commit()
    await session.refresh(new_result)
    return new_result

async def get_test_results_with_users(session: AsyncSession, test_id: str) -> List[Tuple]:

    from src.database.sign_data import User 
    stmt = select(
        Result.user_id,
        User.first_name, 
        User.last_name, 
        User.phone_number,
        Result.correct_count, 
        Result.total_questions,
        Result.user_answers_key,
    ).join(
        User, User.tg_id == Result.user_id
    ).where(
        Result.test_id == test_id
    ).order_by(
        desc(Result.correct_count), asc(Result.created_at)
    )

    result = await session.execute(stmt)
    return result.all()

async def get_unique_user_ids_for_test(session: AsyncSession, test_id: str) -> List[int]:
    stmt = select(Result.user_id).where(Result.test_id == test_id).distinct()
    result = await session.execute(stmt)
    return result.scalars().all()

async def delete_results_by_test_id(session: AsyncSession, test_id: str) -> int:

    stmt = delete(Result).where(Result.test_id == test_id)
    result = await session.execute(stmt)

    return result.rowcount