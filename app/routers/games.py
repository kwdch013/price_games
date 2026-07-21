"""ゲームの CRUD と集計 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Game
from app.schemas import GameCreate, GameRead, GameUpdate, Medium, Summary
from app.services.loss import pile_loss, price_diff_loss

router = APIRouter(prefix="/games", tags=["games"])


def _to_read(game: Game) -> GameRead:
	"""モデルへ損失計算を付与してレスポンス化する"""
	return GameRead(
		id=game.id,  # type: ignore[arg-type]  # 永続化済みなら必ず採番されている
		title=game.title,
		medium=game.medium,
		purchase_price=game.purchase_price,
		current_price=game.current_price,
		progress=game.progress,
		note=game.note,
		steam_appid=game.steam_appid,
		created_at=game.created_at,
		pile_loss=pile_loss(game.purchase_price, game.progress),
		price_diff_loss=price_diff_loss(game.purchase_price, game.current_price),
	)


def _get_or_404(session: Session, game_id: int) -> Game:
	game = session.get(Game, game_id)
	if game is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ゲームが見つかりません")
	return game


@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
def create_game(payload: GameCreate, session: Session = Depends(get_session)) -> GameRead:
	"""ゲームを登録する"""
	game = Game(
		title=payload.title,
		medium=payload.medium.value,
		purchase_price=payload.purchase_price,
		current_price=payload.current_price,
		progress=payload.progress,
		note=payload.note,
		steam_appid=payload.steam_appid,
	)
	session.add(game)
	session.commit()
	session.refresh(game)
	return _to_read(game)


@router.get("", response_model=list[GameRead])
def list_games(session: Session = Depends(get_session)) -> list[GameRead]:
	"""登録済みゲームを新しい順で一覧する"""
	games = session.exec(select(Game).order_by(Game.created_at.desc())).all()  # type: ignore[attr-defined]
	return [_to_read(g) for g in games]


@router.get("/summary", response_model=Summary)
def summary(session: Session = Depends(get_session)) -> Summary:
	"""損失の集計（積みゲー損失合計・価格差損失合計・総額）"""
	games = session.exec(select(Game)).all()
	total_pile = sum(pile_loss(g.purchase_price, g.progress) for g in games)
	total_diff = sum(
		d
		for g in games
		if (d := price_diff_loss(g.purchase_price, g.current_price)) is not None
	)
	return Summary(
		count=len(games),
		total_pile_loss=total_pile,
		total_price_diff_loss=total_diff,
		total_loss=total_pile + total_diff,
	)


@router.get("/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)) -> GameRead:
	"""1件取得する"""
	return _to_read(_get_or_404(session, game_id))


@router.patch("/{game_id}", response_model=GameRead)
def update_game(
	game_id: int, payload: GameUpdate, session: Session = Depends(get_session)
) -> GameRead:
	"""部分更新する"""
	game = _get_or_404(session, game_id)
	data = payload.model_dump(exclude_unset=True)
	# 媒体は Enum で来るため文字列へ変換して保存する
	if isinstance(data.get("medium"), Medium):
		data["medium"] = data["medium"].value
	for key, value in data.items():
		setattr(game, key, value)
	session.add(game)
	session.commit()
	session.refresh(game)
	return _to_read(game)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: int, session: Session = Depends(get_session)) -> None:
	"""削除する"""
	game = _get_or_404(session, game_id)
	session.delete(game)
	session.commit()
