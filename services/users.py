from fastapi import HTTPException
import random
from uuid import uuid4

from utils.main import get_token_expires, check_email, check_token_expires, send_email, check_username
from schemas.users import User, CheckEmail, Creds, RegisterUser, UserProfile, Token, LoginUser, ChangeUserUsername, CheckCode, ChangeUserEmail, ChangeUserPassword, ChangeUserPhoto, TokenAuth, LoginUserProfile, SetNewPassword
from db.users import find_user, add_user, change_user

class UsersService:
  # register_user
  def register_user(self, data: RegisterUser) -> LoginUserProfile:
    if data.auth.password != data.check_password:
      raise HTTPException(status_code=400, detail="Пароли не совпадают")

    user: User = find_user(data.auth.email)
    if user != None:
      raise HTTPException(status_code=406, detail="Пользователь с таким Email уже зарегистрирован")
    else:
      new_user: User = User(
        id=str(uuid4()),
        token=Token(
          token="token_" + str(uuid4()),
          expires=get_token_expires()
        ),
        auth=Creds(
          email=data.auth.email,
          password=data.auth.password
        ),
        username="",
        photo="",
        role="user",
        code=""
      )
      
      add_user(new_user)
      return LoginUserProfile(
          id=new_user.id,
          username=new_user.username,
          email=new_user.auth.email,
          photo=new_user.photo,
          token=new_user.token.token,
          role=new_user.role,
        )

  # login_user
  def login_user(self, data: LoginUser) -> LoginUserProfile:
    user: User = self._auth(Creds(email=data.auth.email, password=data.auth.password))
    if user == None: user = self._token_auth(TokenAuth(token=data.token_auth.token))
    if user:
      user.token.token = "token_" + str(uuid4())
      user.token.expires = get_token_expires()

      change_user(user)
      return LoginUserProfile(
        id=user.id,
        username=user.username,
        email=user.auth.email,
        photo=user.photo,
        token=user.token.token,
        role=user.role,
      )
    
    if(len(data.token_auth.token) != 0):
      raise HTTPException(status_code=404, detail="")
    raise HTTPException(status_code=404, detail="Пользователь не найден")

  # logout_user
  def logout_user(self, data: TokenAuth) -> str:
    user: User = self._token_auth(TokenAuth(token=data.token))
    if user:
      user.token.token = ""
      user.token.expires = 0
      change_user(user)
      return user.id
        
    raise HTTPException(status_code=404, detail="Пользователь не найден")

  # user_password_recovery_get_email
  def user_password_recovery_get_email(self, data: CheckEmail) -> str:
    email: str = data.email
    if check_email(email) == False:
      raise HTTPException(status_code=422, detail="Некорректно введён Email")
    user: User = find_user(email)
    if user != None:
      code: str = str(random.randint(1000, 9999))
      send_email(
        email=email,
        message_title="Код для изменения пароля",
        message=code
      )
      user.code = code
      change_user(user)
      return user.auth.email
    else:
      raise HTTPException(status_code=404, detail="Пользователь не найден")

  # user_password_recovery_get_code
  def user_password_recovery_get_code(self, data: CheckCode) -> CheckCode:
    user: User = find_user(data.email)
    if user != None and user.code == data.code:
      return CheckCode(email=user.auth.email, code=user.code)
    raise HTTPException(status_code=400, detail="Код введен неверно")

  # user_password_recovery_change_password
  def user_password_recovery_change_password(self, data: SetNewPassword) -> bool:
    user: User = find_user(data.email)
    if user != None:
      if user.code != data.code:
        raise HTTPException(status_code=400, detail="Неверный код")
      if data.new_password.new_password != data.new_password.check_new_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
      user.code = ""
      user.auth.password = data.new_password.new_password
      user.token.token = ""
      user.token.expires = 0
      change_user(user)
      return user.id
    else:
      raise HTTPException(status_code=400, detail="Пользователь не найден")

  # change_username
  def change_username(self, data: ChangeUserUsername) -> str:
    user: User = self._token_auth(TokenAuth(token=data.user.token))
    if not check_username(data.username):
      raise HTTPException(status_code=400, detail="Имя пользователя имеет недопустимые символы")
    user.username = data.username
    change_user(user)
    return user.id

  # change_email
  def change_email(self, data: ChangeUserEmail) -> str:
    user: User = self._token_auth(TokenAuth(token=data.user.token))
    check_user: User = find_user(data.email)
    if check_user != None and (check_user.id != user.id):
      raise HTTPException(status_code=404, detail="Пользователь с таким Email уже существует")
    if check_user != None and check_user.id == user.id:
      return user.id

    send_email(
      email=user.auth.email,
      message_title="Изменение электронной почты",
      message="Ваша почта была изменена. Новая почта: " + data.email
    )
    user.auth.email = data.email
    change_user(user)
    return user.id

  # change_photo
  def change_photo(self, data: ChangeUserPhoto) -> str:
    user: User = self._token_auth(TokenAuth(token=data.user.token))
    user.photo = data.photo
    change_user(user)
    return user.id

  # change_password
  def change_password(self, data: ChangeUserPassword) -> str:
    user: User = self._token_auth(TokenAuth(token=data.user.token))
    if user.auth.password != data.old_password:
      raise HTTPException(status_code=400, detail="Неверный пароль")
    elif data.new_password.new_password != data.new_password.check_new_password:
      raise HTTPException(status_code=400, detail="Пароли не совпадают")
    else:
      user.auth.password = data.new_password.new_password
      change_user(user)
      return user.id
  
  # _auth
  def _auth(self, data: Creds) -> User:
    user: User = find_user(data.email)
    if user != None and user.auth.password == data.password:
      return user
    return None
  
  # _token_auth
  def _token_auth(self, data: TokenAuth) -> User:
    user: User = find_user(data.token)
    if user != None and check_token_expires(user.token.expires):
      return user
    raise HTTPException(status_code=404, detail="Пользователь не найден")

  # _check_admin
  def _check_admin(self, data: User) -> bool:
    user: User = find_user(data.id)
    if user.role == "admin": return True
    return False

users_service: UsersService = UsersService()