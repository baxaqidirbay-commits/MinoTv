from aiogram.fsm.state import State, StatesGroup


class UserMovieState(StatesGroup):
    waiting_for_code = State()
    waiting_for_query = State()


class AddMovieState(StatesGroup):
    waiting_for_forward = State()
    waiting_for_title = State()
    waiting_for_code = State()
    waiting_for_category = State()
    waiting_for_year = State()
    waiting_for_description = State()
    waiting_for_poster = State()
    waiting_for_confirm = State()


class EditMovieState(StatesGroup):
    waiting_for_value = State()


class DeleteMovieState(StatesGroup):
    waiting_for_confirm = State()
