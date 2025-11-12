from sqlalchemy import Column, String, BigInteger, Boolean, select, update, func, or_, delete
from aiocache import cached
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.database.base import Base


class Test(Base):
    __tablename__ = 'tests'
    
    # id: Matn ID
    id = Column(BigInteger, primary_key=True)
    test_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    creator_id = Column(BigInteger, nullable=False) 
    status = Column(Boolean, default=True, nullable=False)
    answer = Column(String, nullable=False) 
    
    def __repr__(self):
        return f"<Test(id={self.id}, title='{self.title}')>"


async def add_new_test(
    session: AsyncSession,
    test_id: int,
    title: str,
    creator_id: int,
    answer: str,
    status: bool = True
) -> Test:
    new_test = Test(
        id=test_id,     
        title=title,
        test_id=test_id,
        answer=answer, 
        creator_id=creator_id,
        status=status
    )
    session.add(new_test)
    await session.commit()
    await session.refresh(new_test)
    return new_test


@cached(ttl=300, key_builder=lambda f, *args, **kwargs: args[1])
async def get_test_by_id(session: AsyncSession, test_id: int) -> Optional[Test]:
    stmt = select(Test).where(Test.id == test_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def deactivate_test(session: AsyncSession, test_id: int) -> bool:
    stmt = update(Test).where(Test.id == test_id).values(status=False)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0 

async def get_inactive_tests(session: AsyncSession) -> list:
    stmt = select(Test).where(Test.status == False)
    result = await session.execute(stmt)
    inactive_tests = result.scalars().all()
    
    return inactive_tests

async def delete_test_by_id(session: AsyncSession, test_id: int) -> bool:
    stmt = delete(Test).where(Test.id == test_id)
    result = await session.execute(stmt)
    
    if result.rowcount > 0:
        return True
    else:
        return False