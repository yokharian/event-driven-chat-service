import dataclasses
import typing

from aws_lambda_powertools import Logger

logger = Logger()


@dataclasses.dataclass
class QueryBuilder:
    select_columns: list[str]
    from_: list[str] = dataclasses.field(default_factory=list)
    group_by: list[str] = dataclasses.field(default_factory=list)
    order_by: list[str] = dataclasses.field(default_factory=list)
    join: list[tuple[str, str, str]] = dataclasses.field(default_factory=list)
    where_conditions: list[str] = dataclasses.field(default_factory=list)
    search_aliases: typing.Optional[dict[str, str]] = dataclasses.field(
        default_factory=dict
    )
    search_operators: typing.Optional[dict[str, str]] = dataclasses.field(
        default_factory=dict
    )
    initial_sql: str = dataclasses.field(init=False)
    initial_count_sql: str = dataclasses.field(init=False)

    def __post_init__(self):
        select_ = ", ".join(self.select_columns)
        from_ = ", ".join(self.from_)
        self.initial_sql = f"SELECT {select_}\n FROM {from_}\n"
        self.initial_count_sql = f"SELECT COUNT(*) as total\n FROM {from_}\n"

    def build_sql_query(
        self,
        params: dict,
        limit: typing.Optional[int] = None,
        offset: typing.Optional[int] = 0,
    ) -> tuple[str, dict]:
        new_params = (params or {}).copy()
        sql = self.initial_sql

        if self.join:
            joins = []
            for j, t, c in self.join:
                joins.append(f"{j} JOIN {t} on ({c})")
            joins = " ".join(joins)
            sql = f"{sql} {joins}"

        if params is not None:
            conditions = self.where_conditions.copy()
            for key, _value in params.items():
                if _value is None:
                    continue
                search_column = self.search_aliases.get(key, key)
                search_operator = self.search_operators.get(key, "=")
                conditions.append(f"{search_column} {search_operator} %({key})s")
            if conditions:
                where_clause = " AND ".join(conditions)
                sql = f"{sql} WHERE {where_clause}"

        if self.group_by:
            group_by_clause = ", ".join(self.group_by)
            sql = f"{sql} GROUP BY {group_by_clause}"

        if self.order_by:
            order_by_clause = ", ".join(self.order_by)
            sql = f"{sql} ORDER BY {order_by_clause}"

        if limit:
            new_params.update({"limit_param": limit, "offset_param": offset or 0})
            sql = f"{sql} LIMIT %(limit_param)s OFFSET %(offset_param)s"

        return sql, new_params

    def build_sql_with_count_query(
        self,
        params: dict,
        limit: typing.Optional[int] = None,
        offset: typing.Optional[int] = 0,
    ) -> tuple[str, str, dict]:
        new_params = (params or {}).copy()
        sql = self.initial_sql
        sql_count = self.initial_count_sql

        if self.join:
            joins = []
            for j, t, c in self.join:
                joins.append(f"{j} JOIN {t} on ({c})")
            joins = " ".join(joins)
            sql = f"{sql} {joins}"
            sql_count = f"{sql} {joins}"

        if params is not None:
            conditions = self.where_conditions.copy()
            for key, _value in params.items():
                if _value is None:
                    continue
                search_column = self.search_aliases.get(key, key)
                search_operator = self.search_operators.get(key, "=")
                conditions.append(f"{search_column} {search_operator} %({key})s")
            if conditions:
                where_clause = " AND ".join(conditions)
                sql = f"{sql} WHERE {where_clause}"
                sql_count = f"{sql} WHERE {where_clause}"

        if self.group_by:
            group_by_clause = ", ".join(self.group_by)
            sql = f"{sql} GROUP BY {group_by_clause}"
            sql_count = f"{sql} GROUP BY {group_by_clause}"

        if self.order_by:
            order_by_clause = ", ".join(self.order_by)
            sql = f"{sql} ORDER BY {order_by_clause}"

        if limit:
            new_params.update({"limit_param": limit, "offset_param": offset or 0})
            sql = f"{sql} LIMIT %(limit_param)s OFFSET %(offset_param)s"

        return sql, sql_count, new_params
