from fastapi import HTTPException
from schemas.animals import Animal, CreateAnimal, Breed, CreateBreed
from db.animals import get_animals, add_animal, find_animal
from db.breeds import get_breeds, add_breed
from db.users import find_user
from uuid import uuid4
from services.users import users_service

class AnimalsService:
  def get_animals(self) -> list[Animal]:
    animals: list[Animal] = get_animals()
    return animals

  def add_animal(self, data: CreateAnimal):
    user = users_service._token_auth(data.admin)
    
    if not users_service._check_admin(user):
      raise HTTPException(status_code=403, detail="Отказано в доступе")

    new_animal: Animal = Animal(
      id=str(uuid4()),
      name=data.name,
    )

    add_animal(new_animal)
    return new_animal
  
  def get_breeds(self, animal_id: str) -> list[Breed]:
    breeds: list[Animal] = get_breeds(animal_id)
    return breeds
  
  def add_breed(self, data: CreateBreed):
    user = users_service._token_auth(data.admin)
    
    if not users_service._check_admin(user):
      raise HTTPException(status_code=403, detail="Отказано в доступе")
    
    animal = find_animal(data.animal_id)
    
    if animal == None: raise HTTPException(status_code=404, detail="Животное с переданным id не найдено")

    new_breed: Breed = Breed(
      id=str(uuid4()),
      name=data.name,
      animal_id=data.animal_id,
    )

    add_breed(new_breed)
    return new_breed

  
animals_service: AnimalsService = AnimalsService()
