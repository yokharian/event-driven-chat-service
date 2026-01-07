from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class IRepository(ABC):
    """
    Data Access Layer Interface (Contract)

    This abstract interface defines the contract that all repository implementations
    must follow. This allows the business layer to be database-agnostic and enables
    easy migration between different database backends.

    All methods return dictionaries representing database records, allowing
    implementations to handle their own serialization/deserialization.
    """

    @abstractmethod
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new item in the database.

        Args:
            item: Dictionary containing the item data to create

        Returns:
            Dictionary representing the created item (may include auto-generated fields)

        Raises:
            RepositoryError: If the creation operation fails
        """
        pass

    @abstractmethod
    def get_by_key(self, *, raise_not_found: bool = True, **keys) -> Optional[Dict[str, Any]]:
        """
        Get an item by its primary key(s).

        Args:
            raise_not_found: If True, raise ObjectNotFoundError when item is not found.
                           If False, return None when item is not found.
            **keys: Primary key field names and values (e.g., id='123')

        Returns:
            Dictionary representing the found item, or None if not found and raise_not_found=False

        Raises:
            ObjectNotFoundError: If item is not found and raise_not_found=True
            RepositoryError: If the retrieval operation fails
        """
        pass

    @abstractmethod
    def get_list(self) -> List[Dict[str, Any]]:
        """
        Get all items from the database.

        Returns:
            List of dictionaries, each representing a database record

        Raises:
            RepositoryError: If the retrieval operation fails
        """
        pass

    @abstractmethod
    def update(self, params: Dict[str, Any], **keys) -> None:
        """
        Update an existing item in the database.

        Args:
            params: Dictionary containing the fields to update and their new values
            **keys: Primary key field names and values to identify the item to update

        Raises:
            ObjectNotFoundError: If the item to update is not found
            RepositoryError: If the update operation fails
        """
        pass

    @abstractmethod
    def delete(self, **keys) -> None:
        """
        Delete an item from the database.

        Args:
            **keys: Primary key field names and values to identify the item to delete

        Raises:
            ObjectNotFoundError: If the item to delete is not found
            RepositoryError: If the deletion operation fails
        """
        pass
