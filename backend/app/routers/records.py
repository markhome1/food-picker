from typing import Annotated, Optional, List
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract
from sqlmodel import Session, select, func, col

from ..auth_context import AuthCtxDep, AuthContext
from ..database import engine, get_session
from ..models.record import DiningRecord, DiningRecordCreate, DiningRecordPublic
from ..models.restaurant import Restaurant

router = APIRouter(prefix="/api/records", tags=["dining_records"])

SessionDep = Annotated[Session, Depends(get_session)]


def _filter_records_stmt(stmt, ctx: AuthContext):
    if ctx.auth_required and ctx.couple_account_id is not None:
        return stmt.where(DiningRecord.couple_account_id == ctx.couple_account_id)
    return stmt


@router.post("", response_model=DiningRecordPublic)
def create_record(record: DiningRecordCreate, session: SessionDep, ctx: AuthCtxDep):
    # 验证餐厅存在
    restaurant = session.get(Restaurant, record.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="餐厅不存在")
    if ctx.auth_required and restaurant.couple_account_id != ctx.couple_account_id:
        raise HTTPException(status_code=404, detail="餐厅不存在")

    db_obj = DiningRecord.model_validate(record)
    if ctx.auth_required:
        db_obj.couple_account_id = ctx.couple_account_id
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return _to_public(db_obj, restaurant.name)


@router.get("", response_model=List[DiningRecordPublic])
def list_records(
    session: SessionDep,
    ctx: AuthCtxDep,
    restaurant_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=200)] = 50,
):
    stmt = select(DiningRecord).order_by(col(DiningRecord.dining_date).desc())
    stmt = _filter_records_stmt(stmt, ctx)

    if restaurant_id:
        stmt = stmt.where(DiningRecord.restaurant_id == restaurant_id)
    if start_date:
        stmt = stmt.where(DiningRecord.dining_date >= start_date)
    if end_date:
        stmt = stmt.where(DiningRecord.dining_date <= end_date)

    stmt = stmt.offset(offset).limit(limit)
    records = session.exec(stmt).all()

    result = []
    for rec in records:
        r = session.get(Restaurant, rec.restaurant_id)
        name = r.name if r else "已删除"
        result.append(_to_public(rec, name))
    return result


@router.get("/stats")
def get_stats(
    session: SessionDep,
    ctx: AuthCtxDep,
    period: str = Query(default="all", pattern="^(all|month)$"),
):
    """统计看板数据"""
    start_date = None
    if period == "month":
        now = datetime.now()
        start_date = date(now.year, now.month, 1)

    return _build_stats(session, start_date=start_date, ctx=ctx)


def _build_stats(
    session: Session, start_date: Optional[date] = None, ctx: Optional[AuthContext] = None
):
    filters = []
    if start_date is not None:
        filters.append(DiningRecord.dining_date >= start_date)
    if ctx and ctx.auth_required and ctx.couple_account_id is not None:
        filters.append(DiningRecord.couple_account_id == ctx.couple_account_id)

    total_count_stmt = select(func.count(DiningRecord.id))
    total_cost_stmt = select(func.sum(DiningRecord.actual_cost))
    if filters:
        for clause in filters:
            total_count_stmt = total_count_stmt.where(clause)
            total_cost_stmt = total_cost_stmt.where(clause)

    total_count = session.exec(total_count_stmt).one()
    total_cost = session.exec(total_cost_stmt).one() or 0

    # 每家餐厅去了几次
    visit_stmt = (
        select(Restaurant.name, func.count(DiningRecord.id).label("visits"))
        .join(Restaurant)
        .group_by(Restaurant.name)
        .order_by(func.count(DiningRecord.id).desc())
    )
    if filters:
        for clause in filters:
            visit_stmt = visit_stmt.where(clause)
    visits = session.exec(visit_stmt).all()

    # 月度消费
    if engine.dialect.name == "sqlite":
        month_expr = func.strftime("%Y-%m", DiningRecord.dining_date)
        monthly_stmt = (
            select(
                month_expr.label("month"),
                func.count(DiningRecord.id).label("count"),
                func.sum(DiningRecord.actual_cost).label("total_cost"),
            )
            .group_by(month_expr)
            .order_by(month_expr.desc())
        )
    else:
        year_expr = extract("year", DiningRecord.dining_date)
        month_num_expr = extract("month", DiningRecord.dining_date)
        monthly_stmt = (
            select(
                year_expr.label("year"),
                month_num_expr.label("month_num"),
                func.count(DiningRecord.id).label("count"),
                func.sum(DiningRecord.actual_cost).label("total_cost"),
            )
            .group_by(year_expr, month_num_expr)
            .order_by(year_expr.desc(), month_num_expr.desc())
        )
    if filters:
        for clause in filters:
            monthly_stmt = monthly_stmt.where(clause)
    monthly = session.exec(monthly_stmt).all()

    if engine.dialect.name == "sqlite":
        monthly_rows = [
            {"month": m[0], "count": m[1], "total_cost": round(m[2] or 0, 2)}
            for m in monthly
        ]
    else:
        monthly_rows = [
            {
                "month": f"{int(m[0]):04d}-{int(m[1]):02d}",
                "count": m[2],
                "total_cost": round(m[3] or 0, 2),
            }
            for m in monthly
        ]

    return {
        "code": 200,
        "data": {
            "total_count": total_count,
            "total_cost": round(total_cost, 2) if total_cost else 0,
            "restaurant_visits": [{"name": v[0], "visits": v[1]} for v in visits],
            "monthly": monthly_rows,
        },
    }


@router.delete("/{record_id}")
def delete_record(record_id: int, session: SessionDep, ctx: AuthCtxDep):
    rec = session.get(DiningRecord, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="记录不存在")
    if ctx.auth_required and rec.couple_account_id != ctx.couple_account_id:
        raise HTTPException(status_code=404, detail="记录不存在")
    session.delete(rec)
    session.commit()
    return {"code": 200, "message": "已删除"}


def _to_public(rec: DiningRecord, restaurant_name: str) -> DiningRecordPublic:
    return DiningRecordPublic(
        **rec.model_dump(),
        restaurant_name=restaurant_name,
    )
