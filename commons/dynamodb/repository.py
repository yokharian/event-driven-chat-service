"""
DEPRECATED: This module is maintained for backward compatibility.

Please use commons.dal.DynamoDBRepository instead.
TableRepository is now an alias to DynamoDBRepository.
"""

from commons.dal.dynamodb_repository import DynamoDBRepository

# Backward compatibility: TableRepository is now an alias to DynamoDBRepository
TableRepository = DynamoDBRepository

# Re-export for backward compatibility
__all__ = ["TableRepository"]
