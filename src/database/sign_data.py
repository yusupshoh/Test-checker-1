from sqlalchemy import Column, BigInteger, String, Boolean, select, update, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any, Tuple
from src.database.base import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    
    tg_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    first_name = Column(String(255), nullable=True) 
    last_name = Column(String(255), nullable=True) 
    phone_number = Column(String(20), nullable=True)
    role = Column(Boolean, default=False, nullable=False) 
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    def __repr__(self):
        return f"<User(tg_id={self.tg_id}, first_name='{self.first_name}')>"



async def add_new_user(
    session: AsyncSession,
    user_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None
) -> Tuple[User, bool]: 
    
    existing_user = await get_user(session, user_id)
    is_new = False
    new_user = None

    if existing_user is None:

        new_user = User(
            tg_id=user_id,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,

        )
        session.add(new_user)
        await session.commit()
        is_new = True
    else:
        new_user = existing_user
        
    return new_user, is_new

async def update_user_info(
    session: AsyncSession,
    tg_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> bool:
    update_values = {}
    
    if first_name is not None:
        update_values['first_name'] = first_name
    if last_name is not None:
        update_values['last_name'] = last_name  
    if phone_number is not None:
        update_values['phone_number'] = phone_number
    if not update_values:
        return False
        
    stmt = update(User).where(User.tg_id == tg_id).values(**update_values)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def check_is_admin(session: AsyncSession, tg_id: int) -> bool:
    stmt = select(User.tg_id).where(User.tg_id == tg_id, User.role == True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None

async def set_admin_status(session: AsyncSession, tg_id: int, is_admin: bool) -> bool:
    stmt = update(User).where(User.tg_id == tg_id).values(role=is_admin)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def get_admin_user_if_exists(session: AsyncSession, tg_id: int) -> Optional[User]:
    stmt = select(User).where(User.tg_id == tg_id, User.role == True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_users_ids(session: AsyncSession) -> List[int]:
    stmt = select(User.tg_id)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]

async def get_all_users_data(session: AsyncSession) -> List[Dict[str, Any]]:
    stmt = select(User.tg_id, User.first_name, User.last_name, User.role)
    result = await session.execute(stmt)
    user_list = []

    for tg_id, first_name, last_name, role in result.all():
        user_list.append({
            'TG ID': tg_id,
            'Ism': first_name if first_name else 'Yo\'q', 
            'Familiya': last_name if last_name else 'Yo\'q',
            'Admin': 'Ha' if role else 'Yo\'q'
        })
        
    return user_list

async def get_new_users_count_since(session: AsyncSession, since_datetime: datetime) -> int:
    stmt = select(func.count()).where(User.created_at >= since_datetime)
    result = await session.execute(stmt)
    return result.scalar_one()

async def get_all_admin_ids(session: AsyncSession) -> List[int]:
    stmt = select(User.tg_id).where(User.role == True)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_users_creation_dates(session: AsyncSession) -> List[datetime.datetime]:
    stmt = select(User.created_at)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def ensure_primary_admin(
        session: AsyncSession,
        tg_id: int,
        first_name: str,
        last_name: Optional[str] = None
) -> bool:
    existing_user = await get_user(session, tg_id)

    if existing_user is None:
        new_admin = User(
            tg_id=tg_id,
            first_name=first_name,
            last_name=last_name,
            role=True,  # Avtomatik admin huquqi
        )
        session.add(new_admin)
        await session.commit()
        return True

    elif not existing_user.role:
        # Foydalanuvchi bor, lekin admin emas, uni admin qilamiz
        update_values = {'role': True}
        if existing_user.first_name is None: update_values['first_name'] = first_name
        if existing_user.last_name is None: update_values['last_name'] = last_name

        if update_values:
            stmt = update(User).where(User.tg_id == tg_id).values(**update_values)
            await session.execute(stmt)
            await session.commit()
            return True

    return False