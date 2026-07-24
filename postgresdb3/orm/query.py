from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, Any, Optional, List, Tuple, Dict, Union
from postgresdb3.orm.expressions import Q

T = TypeVar("T")


@dataclass
class PaginationResult(Generic[T]):
    total: int
    pages: int
    current_page: int
    per_page: int
    has_next: bool
    has_prev: bool
    data: list[T]


_query_cache = {}


class QuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._exclude = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"
        self._join = None
        self._group_by = None
        self._select_for_update = False
        self._cache_ttl = None
        self._select_related = None
        self._prefetch = None

    def _clone(self):
        qs = self.__class__(self.model)
        if isinstance(self._where, dict):
            qs._where = dict(self._where)
        elif isinstance(self._where, list):
            qs._where = list(self._where)
        else:
            qs._where = self._where

        if isinstance(self._exclude, dict):
            qs._exclude = dict(self._exclude)
        elif isinstance(self._exclude, list):
            qs._exclude = list(self._exclude)
        else:
            qs._exclude = self._exclude

        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = list(self._join) if self._join else None
        qs._group_by = self._group_by
        qs._select_for_update = self._select_for_update
        qs._cache_ttl = self._cache_ttl
        qs._select_related = list(self._select_related) if self._select_related else None
        qs._prefetch = list(self._prefetch) if self._prefetch else None
        return qs

    def cache(self, ttl: float = 60.0):
        """
        So'rov natijasini ko'rsatilgan soniya (ttl) davomida keshda saqlaydi.
        """
        qs = self._clone()
        qs._cache_ttl = ttl
        return qs

    def force(self):
        """
        Ommaviy update/delete operatsiyalarini shartsiz (barcha qatorlarda) bajarishga ruxsat beradi.
        """
        qs = self._clone()
        qs._force = True
        return qs

    def update(self, force: bool = False, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(
                    f"{self.model.__name__} modelida '{key}' degan ustun yo'q"
                )

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy update uchun filter sharti kerak! "
                "(Butun jadvalni yangilash uchun force=True yoki .force() ishlating)"
            )

        return self.model.db.update_where(self.model.table, kwargs, where)

    def delete(self, force: bool = False):
        self.model._check_setup()

        where = self._build_where()

        if not where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy delete uchun filter sharti kerak! "
                "(Butun jadvalni o'chirish uchun force=True yoki .force() ishlating)"
            )

        return self.model.db.delete_where(self.model.table, where)

    def join(self, table, on_condition, join_type="INNER JOIN"):
        qs = self._clone()
        if qs._join is None:
            qs._join = []
        qs._join.append((join_type, table, on_condition))
        return qs

    def _build_values_columns(self, fields):
        if not fields:
            return "*"
        parsed_fields = []
        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )

        for field in fields:
            if "__" in field:
                parts = field.split("__")
                rel_name = parts[0]
                col_name = "__".join(parts[1:])
                rel_attr = getattr(self.model, rel_name, None)
                if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                    target_model = rel_attr.related_model
                    target_table = target_model.table
                    db_col = rel_attr.field_name
                    on_condition = f"{self.model.table}.{db_col} = {target_table}.{target_model.get_pk_name()}"
                    if not self._join:
                        self._join = []
                    if not any(j[1] == target_table for j in self._join):
                        self._join.append(("LEFT JOIN", target_table, on_condition))
                    parsed_fields.append(f"{target_table}.{col_name} AS \"{field}\"")
                    continue
            if "." not in field:
                parsed_fields.append(f"{self.model.table}.{field} AS \"{field}\"")
            else:
                parsed_fields.append(field)

        return ", ".join(parsed_fields)

    def _get_columns_sql(self):
        if self._columns != "*":
            columns = self._columns
        elif self._select_related:
            cols = [f"{self.model.table}.{f} AS {f}" for f in self.model._fields.keys()]
            from postgresdb3.orm.relations import (
                ForeignKeyRelation,
                AsyncForeignKeyRelation,
            )
            for rel_str in self._select_related:
                parts = rel_str.split("__")
                curr_model = self.model
                curr_alias = self.model.table
                for p in parts:
                    if p.endswith("_id") and hasattr(curr_model, p[:-3]):
                        rel_name = p[:-3]
                        possible_attr = getattr(curr_model, rel_name, None)
                        if isinstance(possible_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                            db_col = possible_attr.field_name
                            field = curr_model._fields.get(db_col)
                        else:
                            field = curr_model._fields.get(p)
                    else:
                        rel_attr = getattr(curr_model, p, None)
                        rel_name = p
                        if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                            db_col = rel_attr.field_name
                            field = curr_model._fields.get(db_col)
                        else:
                            field = curr_model._fields.get(p)

                    if not field or not hasattr(field, "to"):
                        break

                    curr_model = field.to
                    curr_alias = f"{curr_alias}__{rel_name}"

                if curr_model != self.model:
                    for rf in curr_model._fields.keys():
                        cols.append(f"{curr_alias}.{rf} AS __rel__{rel_str}__{rf}")
            columns = ", ".join(cols)
        elif self._join or (hasattr(self, "_annotations") and self._annotations):
            columns = f"{self.model.table}.*"
        else:
            columns = "*"

        if hasattr(self, "_annotations") and self._annotations:
            for alias, expression in self._annotations.items():
                if hasattr(expression, "to_sql"):
                    columns += f", {expression.to_sql()} AS {alias}"
                else:
                    columns += f", {expression} AS {alias}"

        return columns

    def _hydrate_records(self, records):
        if not records:
            return []
        if isinstance(records, dict) or hasattr(records, "items"):
            records = [records]

        instances = []
        for record in records:
            if isinstance(record, dict):
                row = record
            elif hasattr(record, "_asdict"):
                row = record._asdict()
            elif hasattr(record, "items"):
                row = dict(record)
            else:
                instances.append(self.model._from_record(record))
                continue

            if self._select_related:
                main_data = {k: v for k, v in row.items() if not k.startswith("__rel__")}
                inst = self.model._from_record(main_data)

                sorted_rels = sorted(self._select_related, key=lambda x: len(x.split("__")))
                hydrated_map = {"": inst}

                for rel_str in sorted_rels:
                    prefix = f"__rel__{rel_str}__"
                    rel_data = {k[len(prefix):]: v for k, v in row.items() if k.startswith(prefix)}

                    parts = rel_str.split("__")
                    parent_path = "__".join(parts[:-1])
                    parent_inst = hydrated_map.get(parent_path)
                    current_field = parts[-1]
                    if parent_inst and current_field.endswith("_id") and hasattr(parent_inst.__class__, current_field[:-3]):
                        current_field = current_field[:-3]

                    if parent_inst:
                        rel_attr = getattr(parent_inst.__class__, current_field, None)
                        if rel_attr and hasattr(rel_attr, "related_model"):
                            rmodel = rel_attr.related_model
                            pk_col = rmodel.get_pk_name()
                            if rel_data and rel_data.get(pk_col) is not None:
                                rel_inst = rmodel._from_record(rel_data)
                            else:
                                rel_inst = None
                            setattr(parent_inst, f"_prefetched_{current_field}", rel_inst)
                            if rel_inst:
                                hydrated_map[rel_str] = rel_inst
            else:
                inst = self.model._from_record(row)

            instances.append(inst)

        return instances

    def select_related(self, *fields):
        """
        N+1 muammosini oldini olish uchun yozilgan metod.
        Berilgan ForeignKey maydonlari bo'yicha avtomatik JOIN qiladi (shuningdek zanjirsimon `category__parent` ham qo'llab-quvvatlanadi).
        """
        qs = self._clone()
        if qs._join is None:
            qs._join = []
        if qs._select_related is None:
            qs._select_related = []

        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )
        from .fields.foreign import ManyToMany

        for field_name in fields:
            parts = field_name.split("__")
            curr_model = self.model
            curr_table_alias = self.model.table
            rel_path = []

            for part in parts:
                if part.endswith("_id") and hasattr(curr_model, part[:-3]):
                    rel_name = part[:-3]
                    possible_attr = getattr(curr_model, rel_name, None)
                    if isinstance(possible_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                        db_col = possible_attr.field_name
                        field = curr_model._fields.get(db_col)
                    else:
                        db_col = part
                        field = curr_model._fields.get(part)
                else:
                    rel_attr = getattr(curr_model, part, None)
                    rel_name = part
                    if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                        db_col = rel_attr.field_name
                        field = curr_model._fields.get(db_col)
                    else:
                        field = curr_model._fields.get(part)
                        db_col = part

                if not field or not hasattr(field, "to"):
                    raise ValueError(
                        f"'{part}' (path '{field_name}') xato kiritildi. select_related faqat ForeignKey yoki OneToOne bilan ishlaydi."
                    )

                if isinstance(field, ManyToMany):
                    raise TypeError(
                        f"'{part}' bu ManyToMany! Uning uchun select_related() emas, balki prefetch_related() ishlating."
                    )

                target_model = field.to
                target_table = target_model.table
                rel_path.append(rel_name)
                current_rel_str = "__".join(rel_path)

                join_alias = f"{curr_table_alias}__{rel_name}"
                join_table_expr = f"{target_table} AS {join_alias}"

                on_condition = f"{curr_table_alias}.{db_col} = {join_alias}.{target_model.get_pk_name()}"
                if not any(j[1] == join_table_expr for j in qs._join):
                    qs._join.append(("LEFT JOIN", join_table_expr, on_condition))

                if current_rel_str not in qs._select_related:
                    qs._select_related.append(current_rel_str)

                curr_model = target_model
                curr_table_alias = join_alias

        return qs

    def prefetch_related(self, *fields):
        """
        Ko'pga-ko'p (ManyToMany) va Birga-ko'p (OneToMany) bog'lanishlar uchun N+1 muammosini oldini olish.
        Ushbu metod ma'lumotlarni alohida so'rovlar orqali olib, xotirada bog'lab qo'yadi.
        `category` va `category_id` ko'rinishida ham berish mumkin.
        """
        qs = self._clone()
        if qs._prefetch is None:
            qs._prefetch = []

        normalized_fields = []
        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )
        for field_name in fields:
            if field_name.endswith("_id") and not hasattr(self.model, field_name):
                possible_rel = field_name[:-3]
                if hasattr(self.model, possible_rel):
                    field_name = possible_rel
            normalized_fields.append(field_name)

        qs._prefetch.extend(normalized_fields)
        return qs

    def select_for_update(self):
        """
        Joriy tranzaksiya doirasida tanlangan qatorlarni qulflash (lock) uchun.
        Pessimistic locking (balans yangilash va sh.k. poyga holatlarining oldini olish uchun).
        """
        qs = self._clone()
        qs._select_for_update = True
        return qs

    def _normalize_q(self, q):
        if not q:
            return q
        from postgresdb3.orm.expressions import Q

        if isinstance(q, Q):
            if q.conditions:
                q.conditions = self._process_auto_joins(q.conditions)
            if q.children:
                for i, child in enumerate(q.children):
                    q.children[i] = self._normalize_q(child)
        return q

    def _process_auto_joins(self, kwargs):
        new_kwargs = {}
        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )
        from postgresdb3.orm.base import BaseModel

        def extract_pk(val):
            if isinstance(val, BaseModel):
                return getattr(val, val.get_pk_name())
            return val

        for key, value in kwargs.items():
            if isinstance(value, (list, tuple)):
                value = [extract_pk(v) for v in value]
            else:
                value = extract_pk(value)

            parts = key.split("__")
            field_name = parts[0]

            relation = getattr(self.model, field_name, None)
            is_fk_relation = relation and isinstance(
                relation, (ForeignKeyRelation, AsyncForeignKeyRelation)
            )

            is_fk_comparison = False
            if is_fk_relation:
                if len(parts) == 1:
                    is_fk_comparison = True
                elif len(parts) == 2:
                    lookup_ops = {
                        "eq",
                        "ne",
                        "not",
                        "gt",
                        "gte",
                        "lt",
                        "lte",
                        "like",
                        "ilike",
                        "contains",
                        "icontains",
                        "startswith",
                        "istartswith",
                        "endswith",
                        "iendswith",
                        "in",
                        "not_in",
                        "isnull",
                    }
                    if parts[1] in lookup_ops:
                        is_fk_comparison = True

            if is_fk_comparison:
                parts[0] = relation.field_name
                key = "__".join(parts)

            elif len(parts) >= 2:
                if relation and hasattr(relation, "related_model"):
                    target_table = relation.related_model.table
                    source_col = getattr(relation, "field_name", field_name)
                    target_col = relation.related_model.get_pk_name()

                    join_condition = (
                        f"{self.model.table}.{source_col} = {target_table}.{target_col}"
                    )

                    if not self._join:
                        self._join = []

                    join_exists = any(
                        j[1] == target_table and j[2] == join_condition
                        for j in self._join
                        if isinstance(j, tuple) and len(j) == 3
                    )

                    if not join_exists:
                        self._join.append(("INNER JOIN", target_table, join_condition))

                    new_key = f"{target_table}.{'__'.join(parts[1:])}"
                    new_kwargs[new_key] = value
                    continue

            new_kwargs[key] = value

        return new_kwargs

    def filter(self, *args, **kwargs):
        qs = self._clone()

        if qs._where is None:
            qs._where = []

        if not isinstance(qs._where, list):
            qs._where = [qs._where]

        for arg in args:
            qs._where.append(self._normalize_q(arg))

        if kwargs:
            qs._where.append(self._process_auto_joins(kwargs))

        return qs

    def exclude(self, *args, **kwargs):
        qs = self._clone()

        if qs._exclude is None:
            qs._exclude = []

        if not isinstance(qs._exclude, list):
            qs._exclude = [qs._exclude]

        for arg in args:
            qs._exclude.append(self._normalize_q(arg))

        if kwargs:
            qs._exclude.append(qs._process_auto_joins(kwargs))
        return qs

    def order_by(self, value):
        qs = self._clone()
        qs._order_by = value
        return qs

    def limit(self, value):
        qs = self._clone()
        qs._limit = value
        return qs

    def offset(self, value):
        qs = self._clone()
        qs._offset = value
        return qs

    def columns(self, value):
        qs = self._clone()
        qs._columns = value
        return qs

    def join(self, value):
        qs = self._clone()
        qs._join = value
        return qs

    def group_by(self, value):
        qs = self._clone()
        qs._group_by = value
        return qs

    def values(self, *fields):
        qs = self._clone()
        if fields:
            qs._columns = qs._build_values_columns(fields)
        qs._return_type = "dict"
        return qs

    def values_list(self, *fields, flat=False):
        qs = self._clone()
        if fields:
            qs._columns = qs._build_values_columns(fields)
        qs._return_type = "list"
        qs._flat = flat
        return qs

    def only(self, *fields):
        """
        Faqat ko'rsatilgan ustunlarni yuklaydi. Model obyektlari qaytariladi.
        """
        qs = self._clone()
        if not fields:
            return qs

        pk = self.model.get_pk_name()
        pk_list = [pk] if isinstance(pk, str) else list(pk)

        selected = list(fields)
        for p in pk_list:
            if p not in selected and p in self.model._fields:
                selected.insert(0, p)

        for f in fields:
            if f not in self.model._fields:
                raise ValueError(
                    f"'{f}' ustuni {self.model.__name__} modelida mavjud emas"
                )

        qs._columns = ", ".join(selected)
        return qs

    def defer(self, *fields):
        """
        Ko'rsatilgan ustunlardan tashqari barcha ustunlarni yuklaydi.
        """
        qs = self._clone()
        if not fields:
            return qs

        pk = self.model.get_pk_name()
        pk_set = set([pk] if isinstance(pk, str) else list(pk))
        deferred = set(fields) - pk_set

        selected = [
            f
            for f in self.model._fields
            if f not in deferred and self.model._fields[f].to_sql()
        ]
        qs._columns = ", ".join(selected)
        return qs

    def all(self):
        import time

        cache_key = None
        if getattr(self, "_cache_ttl", None) is not None:
            cache_key = (
                self.model.__name__,
                self._columns,
                str(self._where),
                str(self._order_by),
                self._limit,
                self._offset,
            )
            if cache_key in _query_cache:
                cached_time, cached_res = _query_cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    return cached_res

        where = self._build_where()

        group_by = self._group_by
        if hasattr(self, "_annotations") and self._annotations and not group_by:
            group_by = f"{self.model.table}.{self.model.get_pk_name()}"

        records = self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=group_by,
            order_by=self._get_order_by_sql(),
            limit=self._limit,
            offset=self._offset,
            for_update=self._select_for_update,
        )

        if getattr(self, "_return_type", None) == "dict":
            res = records
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                res = [
                    list(r.values())[0] if isinstance(r, dict) else r[0]
                    for r in records
                ]
            else:
                res = [
                    tuple(r.values()) if isinstance(r, dict) else tuple(r)
                    for r in records
                ]
        else:
            instances = self._hydrate_records(records)
            res = self._process_prefetch(instances)

        if cache_key is not None:
            _query_cache[cache_key] = (time.time(), res)

        return res

    def _process_prefetch(self, instances):
        if hasattr(self, "_prefetch") and self._prefetch and instances:
            for field_name in self._prefetch:
                relation = getattr(self.model, field_name, None)
                if not relation:
                    continue

                pk_name = self.model.get_pk_name()
                instance_pks = [getattr(inst, pk_name) for inst in instances]

                from postgresdb3.orm.relations import (
                    ManyToManyRelation,
                    ReverseRelation,
                    ForeignKeyRelation,
                    AsyncForeignKeyRelation,
                )

                if isinstance(relation, ManyToManyRelation):
                    target_model = relation.target_model
                    through_table = relation.through_table
                    source_col = relation.source_col
                    target_col = relation.target_col

                    placeholders = ", ".join(["%s"] * len(instance_pks))
                    sql = f"SELECT {source_col}, {target_col} FROM {through_table} WHERE {source_col} IN ({placeholders})"

                    conn = self.model.db.pool.getconn()
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(sql, tuple(instance_pks))
                            mapping_records = cursor.fetchall()
                    finally:
                        self.model.db.pool.putconn(conn)

                    mapping_dict = {}
                    target_ids = set()
                    for r in mapping_records:
                        s_id, t_id = r[0], r[1]
                        if s_id not in mapping_dict:
                            mapping_dict[s_id] = []
                        mapping_dict[s_id].append(t_id)
                        target_ids.add(t_id)

                    if target_ids:
                        target_instances = target_model.filter(
                            **{f"{target_model.get_pk_name()}__in": list(target_ids)}
                        ).all()
                        target_map = {
                            getattr(t, target_model.get_pk_name()): t
                            for t in target_instances
                        }

                        for inst in instances:
                            pk = getattr(inst, pk_name)
                            prefetched = [
                                target_map[t_id]
                                for t_id in mapping_dict.get(pk, [])
                                if t_id in target_map
                            ]
                            setattr(inst, f"_prefetched_{field_name}", prefetched)

                elif isinstance(relation, ReverseRelation):
                    related_model = relation.related_model
                    fk_name = relation.fk_name

                    related_instances = related_model.filter(
                        **{f"{fk_name}__in": instance_pks}
                    ).all()

                    for inst in instances:
                        pk = getattr(inst, pk_name)
                        prefetched = [
                            r for r in related_instances if getattr(r, fk_name) == pk
                        ]
                        setattr(inst, f"_prefetched_{field_name}", prefetched)

                elif isinstance(relation, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                    related_model = relation.related_model
                    fk_col = relation.field_name
                    fk_vals = list({getattr(inst, fk_col) for inst in instances if getattr(inst, fk_col, None) is not None})
                    if fk_vals:
                        to_field = relation.to_field
                        related_instances = related_model.filter(**{f"{to_field}__in": fk_vals}).all()
                        related_map = {getattr(r, to_field): r for r in related_instances}
                        for inst in instances:
                            fk_val = getattr(inst, fk_col, None)
                            if fk_val in related_map:
                                setattr(inst, f"_prefetched_{field_name}", related_map[fk_val])

        return instances

    def first(self):
        where = self._build_where()
        records = self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._get_order_by_sql(),
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=False,
            for_update=self._select_for_update,
        )
        if not records:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return records[0]
        elif getattr(self, "_return_type", None) == "list":
            rec = records[0]
            if getattr(self, "_flat", False):
                return list(rec.values())[0] if isinstance(rec, dict) else rec[0]
            return tuple(rec.values()) if isinstance(rec, dict) else tuple(rec)

        instances = self._hydrate_records(records)
        instances = self._process_prefetch(instances)
        return instances[0] if instances else None

    def last(self):
        where = self._build_where()
        records = self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._get_reverse_order_by_sql(),
            limit=1,
            offset=self._offset,
            fetchone=False,
            for_update=self._select_for_update,
        )
        if not records:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return records[0]
        elif getattr(self, "_return_type", None) == "list":
            rec = records[0]
            if getattr(self, "_flat", False):
                return list(rec.values())[0] if isinstance(rec, dict) else rec[0]
            return tuple(rec.values()) if isinstance(rec, dict) else tuple(rec)

        instances = self._hydrate_records(records)
        instances = self._process_prefetch(instances)
        return instances[0] if instances else None

    def get_or_create(self, defaults=None, **kwargs):
        qs = self.filter(**kwargs)
        obj = qs.first()
        if obj:
            return obj, False

        params = kwargs.copy()
        if defaults:
            params.update(defaults)

        return self.model.create(**params), True

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        qs = self.filter(**kwargs)
        obj = qs.first()
        if obj:
            for key, value in defaults.items():
                setattr(obj, key, value)
            obj.save()
            return obj, False

        params = kwargs.copy()
        params.update(defaults)
        return self.model.create(**params), True

    def update(self, force: bool = False, **kwargs):
        for name, field in self.model._fields.items():
            if getattr(field, "auto_now", False) and name not in kwargs:
                kwargs[name] = field.get_current_value()
        if not kwargs:
            return 0
        where = self._build_where()
        has_where = where and (not isinstance(where, Q) or where.conditions or where.children)
        if not has_where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy update uchun filter berish shart! (Barcha qatorlarni o'zgartirish uchun force=True yoki .force() ishlating)"
            )
        return self.model.db.update_where(self.model.table, kwargs, where=where)

    def delete(self, force: bool = False):
        where = self._build_where()
        has_where = where and (not isinstance(where, Q) or where.conditions or where.children)
        if not has_where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy delete uchun filter berish shart! (Barcha qatorlarni o'chirish uchun force=True yoki .force() ishlating)"
            )
        return self.model.db.delete_where(self.model.table, where=where)

    def count(self):
        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns="COUNT(*)",
            where=where,
            join=self._join,
            fetchone=True,
        )
        if isinstance(record, dict) or hasattr(record, "keys"):
            return list(record.values())[0]
        return record[0] if record else 0

    def aggregate(self, **kwargs):
        columns = []
        for alias, agg in kwargs.items():
            columns.append(f"{agg.to_sql()} AS {alias}")

        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns=", ".join(columns),
            where=where,
            join=self._join,
            fetchone=True,
        )
        return dict(record) if record else {}

    def paginate(self, page: int, per_page: int):
        total = self.count()
        pages = (total + per_page - 1) // per_page
        data = self.limit(per_page).offset((page - 1) * per_page).all()
        return PaginationResult(
            total=total,
            pages=pages,
            current_page=page,
            per_page=per_page,
            has_next=page < pages,
            has_prev=page > 1,
            data=data,
        )

    def exists(self):
        where = self._build_where()
        return self.model.db.exists_where(
            self.model.table,
            where=where,
            join=self._join,
            group_by=self._group_by,
        )

    def _get_order_by_sql(self):
        order_by = self._order_by
        if not order_by:
            order_by = self.model._meta_options.get("ordering", None)

        if not order_by:
            return None

        if isinstance(order_by, str):
            order_by = [order_by]

        parts = []
        for item in order_by:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if item.startswith("-"):
                col = item[1:].strip()
                direction = "DESC"
            else:
                col = item.strip()
                direction = "ASC"

            if "." not in col:
                col = f"{self.model.table}.{col}"

            parts.append(f"{col} {direction}")
        return ", ".join(parts) if parts else None

    def _get_reverse_order_by_sql(self):
        order_sql = self._get_order_by_sql()
        if not order_sql:
            pk_name = self.model.get_pk_name()
            return f"{self.model.table}.{pk_name} DESC"

        parts = []
        for part in order_sql.split(","):
            part = part.strip()
            if part.endswith(" DESC"):
                parts.append(part[:-5] + " ASC")
            elif part.endswith(" ASC"):
                parts.append(part[:-4] + " DESC")
            else:
                parts.append(part + " DESC")
        return ", ".join(parts)

    def _build_where(self):
        from postgresdb3.orm.expressions import Q

        final_q = Q()

        if self._where:
            if isinstance(self._where, dict):
                final_q &= Q(**self._where)
            elif isinstance(self._where, list):
                for w in self._where:
                    if isinstance(w, Q):
                        final_q &= w
                    elif isinstance(w, dict):
                        final_q &= Q(**w)

        if self._exclude:
            if isinstance(self._exclude, dict):
                final_q &= ~Q(**self._exclude)
            elif isinstance(self._exclude, list):
                for e in self._exclude:
                    if isinstance(e, Q):
                        final_q &= ~e
                    elif isinstance(e, dict):
                        final_q &= ~Q(**e)

        return final_q if (final_q.conditions or final_q.children) else None


class AsyncQuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._exclude = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"
        self._join = None
        self._group_by = None
        self._select_for_update = False
        self._select_related = None
        self._prefetch = None

    def _clone(self):
        qs = self.__class__(self.model)
        if isinstance(self._where, dict):
            qs._where = dict(self._where)
        elif isinstance(self._where, list):
            qs._where = list(self._where)
        else:
            qs._where = self._where

        if isinstance(self._exclude, dict):
            qs._exclude = dict(self._exclude)
        elif isinstance(self._exclude, list):
            qs._exclude = list(self._exclude)
        else:
            qs._exclude = self._exclude

        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = list(self._join) if self._join else None
        qs._group_by = self._group_by
        qs._select_for_update = self._select_for_update
        qs._select_related = list(self._select_related) if self._select_related else None
        qs._prefetch = list(self._prefetch) if self._prefetch else None
        return qs

    def force(self):
        """
        Ommaviy update/delete operatsiyalarini shartsiz (barcha qatorlarda) bajarishga ruxsat beradi.
        """
        qs = self._clone()
        qs._force = True
        return qs

    async def update(self, force: bool = False, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(
                    f"{self.model.__name__} modelida '{key}' degan ustun yo'q"
                )

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy update uchun filter sharti kerak! "
                "(Butun jadvalni yangilash uchun force=True yoki .force() ishlating)"
            )

        return await self.model.db.update_where(self.model.table, kwargs, where)

    async def delete(self, force: bool = False):
        self.model._check_setup()

        where = self._build_where()

        if not where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy delete uchun filter sharti kerak! "
                "(Butun jadvalni o'chirish uchun force=True yoki .force() ishlating)"
            )

        return await self.model.db.delete_where(self.model.table, where)

    def _build_values_columns(self, fields):
        if not fields:
            return "*"
        parsed_fields = []
        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )

        for field in fields:
            if "__" in field:
                parts = field.split("__")
                rel_name = parts[0]
                col_name = "__".join(parts[1:])
                rel_attr = getattr(self.model, rel_name, None)
                if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                    target_model = rel_attr.related_model
                    target_table = target_model.table
                    db_col = rel_attr.field_name
                    on_condition = f"{self.model.table}.{db_col} = {target_table}.{target_model.get_pk_name()}"
                    if not self._join:
                        self._join = []
                    if not any(j[1] == target_table for j in self._join):
                        self._join.append(("LEFT JOIN", target_table, on_condition))
                    parsed_fields.append(f"{target_table}.{col_name} AS \"{field}\"")
                    continue
            if "." not in field:
                parsed_fields.append(f"{self.model.table}.{field} AS \"{field}\"")
            else:
                parsed_fields.append(field)

        return ", ".join(parsed_fields)

    def _get_columns_sql(self):
        if self._columns != "*":
            columns = self._columns
        elif self._select_related:
            cols = [f"{self.model.table}.{f} AS {f}" for f in self.model._fields.keys()]
            from postgresdb3.orm.relations import (
                ForeignKeyRelation,
                AsyncForeignKeyRelation,
            )
            for rel_str in self._select_related:
                parts = rel_str.split("__")
                curr_model = self.model
                curr_alias = self.model.table
                for p in parts:
                    if p.endswith("_id") and hasattr(curr_model, p[:-3]):
                        rel_name = p[:-3]
                        possible_attr = getattr(curr_model, rel_name, None)
                        if isinstance(possible_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                            db_col = possible_attr.field_name
                            field = curr_model._fields.get(db_col)
                        else:
                            field = curr_model._fields.get(p)
                    else:
                        rel_attr = getattr(curr_model, p, None)
                        rel_name = p
                        if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                            db_col = rel_attr.field_name
                            field = curr_model._fields.get(db_col)
                        else:
                            field = curr_model._fields.get(p)

                    if not field or not hasattr(field, "to"):
                        break

                    curr_model = field.to
                    curr_alias = f"{curr_alias}__{rel_name}"

                if curr_model != self.model:
                    for rf in curr_model._fields.keys():
                        cols.append(f"{curr_alias}.{rf} AS __rel__{rel_str}__{rf}")
            columns = ", ".join(cols)
        elif self._join or (hasattr(self, "_annotations") and self._annotations):
            columns = f"{self.model.table}.*"
        else:
            columns = "*"

        if hasattr(self, "_annotations") and self._annotations:
            for alias, expression in self._annotations.items():
                if hasattr(expression, "to_sql"):
                    columns += f", {expression.to_sql()} AS {alias}"
                else:
                    columns += f", {expression} AS {alias}"

        return columns

    def _hydrate_records(self, records):
        if not records:
            return []
        if isinstance(records, dict) or hasattr(records, "items"):
            records = [records]

        instances = []
        for record in records:
            if isinstance(record, dict):
                row = record
            elif hasattr(record, "_asdict"):
                row = record._asdict()
            elif hasattr(record, "items"):
                row = dict(record)
            else:
                instances.append(self.model._from_record(record))
                continue

            if self._select_related:
                main_data = {k: v for k, v in row.items() if not k.startswith("__rel__")}
                inst = self.model._from_record(main_data)

                sorted_rels = sorted(self._select_related, key=lambda x: len(x.split("__")))
                hydrated_map = {"": inst}

                for rel_str in sorted_rels:
                    prefix = f"__rel__{rel_str}__"
                    rel_data = {k[len(prefix):]: v for k, v in row.items() if k.startswith(prefix)}

                    parts = rel_str.split("__")
                    parent_path = "__".join(parts[:-1])
                    parent_inst = hydrated_map.get(parent_path)
                    current_field = parts[-1]
                    if parent_inst and current_field.endswith("_id") and hasattr(parent_inst.__class__, current_field[:-3]):
                        current_field = current_field[:-3]

                    if parent_inst:
                        rel_attr = getattr(parent_inst.__class__, current_field, None)
                        if rel_attr and hasattr(rel_attr, "related_model"):
                            rmodel = rel_attr.related_model
                            pk_col = rmodel.get_pk_name()
                            if rel_data and rel_data.get(pk_col) is not None:
                                rel_inst = rmodel._from_record(rel_data)
                            else:
                                rel_inst = None
                            setattr(parent_inst, f"_prefetched_{current_field}", rel_inst)
                            if rel_inst:
                                hydrated_map[rel_str] = rel_inst
            else:
                inst = self.model._from_record(row)

            instances.append(inst)

        return instances

    async def _process_prefetch(self, instances):
        if hasattr(self, "_prefetch") and self._prefetch and instances:
            for field_name in self._prefetch:
                relation = getattr(self.model, field_name, None)
                if not relation:
                    continue

                pk_name = self.model.get_pk_name()
                instance_pks = [getattr(inst, pk_name) for inst in instances]

                from postgresdb3.orm.relations import (
                    ManyToManyRelation,
                    AsyncReverseRelation,
                    ForeignKeyRelation,
                    AsyncForeignKeyRelation,
                )

                if isinstance(relation, ManyToManyRelation):
                    target_model = relation.target_model
                    through_table = relation.through_table
                    source_col = relation.source_col
                    target_col = relation.target_col

                    placeholders = ", ".join(
                        [f"${i+1}" for i in range(len(instance_pks))]
                    )
                    sql = f"SELECT {source_col}, {target_col} FROM {through_table} WHERE {source_col} IN ({placeholders})"

                    mapping_records = await self.model.db._manager(
                        sql, *instance_pks, fetchall=True
                    )

                    mapping_dict = {}
                    target_ids = set()
                    for r in mapping_records:
                        s_id, t_id = r[source_col], r[target_col]
                        if s_id not in mapping_dict:
                            mapping_dict[s_id] = []
                        mapping_dict[s_id].append(t_id)
                        target_ids.add(t_id)

                    if target_ids:
                        target_instances = await target_model.filter(
                            **{f"{target_model.get_pk_name()}__in": list(target_ids)}
                        ).all()
                        target_map = {
                            getattr(t, target_model.get_pk_name()): t
                            for t in target_instances
                        }

                        for inst in instances:
                            pk = getattr(inst, pk_name)
                            prefetched = [
                                target_map[t_id]
                                for t_id in mapping_dict.get(pk, [])
                                if t_id in target_map
                            ]
                            setattr(inst, f"_prefetched_{field_name}", prefetched)

                elif isinstance(relation, AsyncReverseRelation):
                    related_model = relation.related_model
                    fk_name = relation.fk_name

                    related_instances = await related_model.filter(
                        **{f"{fk_name}__in": instance_pks}
                    ).all()

                    for inst in instances:
                        pk = getattr(inst, pk_name)
                        prefetched = [
                            r for r in related_instances if getattr(r, fk_name) == pk
                        ]
                        setattr(inst, f"_prefetched_{field_name}", prefetched)

                elif isinstance(relation, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                    related_model = relation.related_model
                    fk_col = relation.field_name
                    fk_vals = list({getattr(inst, fk_col) for inst in instances if getattr(inst, fk_col, None) is not None})
                    if fk_vals:
                        to_field = relation.to_field
                        related_instances = await related_model.filter(**{f"{to_field}__in": fk_vals}).all()
                        related_map = {getattr(r, to_field): r for r in related_instances}
                        for inst in instances:
                            fk_val = getattr(inst, fk_col, None)
                            if fk_val in related_map:
                                setattr(inst, f"_prefetched_{field_name}", related_map[fk_val])

        return instances

    def select_related(self, *fields):
        """
        N+1 muammosini oldini olish uchun yozilgan asinxron metod.
        Berilgan ForeignKey maydonlari bo'yicha avtomatik JOIN qiladi (shuningdek zanjirsimon `category__parent` ham qo'llab-quvvatlanadi).
        """
        qs = self._clone()
        if qs._join is None:
            qs._join = []
        if qs._select_related is None:
            qs._select_related = []

        from postgresdb3.orm.relations import (
            ForeignKeyRelation,
            AsyncForeignKeyRelation,
        )
        from .fields.foreign import ManyToMany

        for field_name in fields:
            parts = field_name.split("__")
            curr_model = self.model
            curr_table_alias = self.model.table
            rel_path = []

            for part in parts:
                if part.endswith("_id") and hasattr(curr_model, part[:-3]):
                    rel_name = part[:-3]
                    possible_attr = getattr(curr_model, rel_name, None)
                    if isinstance(possible_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                        db_col = possible_attr.field_name
                        field = curr_model._fields.get(db_col)
                    else:
                        db_col = part
                        field = curr_model._fields.get(part)
                else:
                    rel_attr = getattr(curr_model, part, None)
                    rel_name = part
                    if isinstance(rel_attr, (ForeignKeyRelation, AsyncForeignKeyRelation)):
                        db_col = rel_attr.field_name
                        field = curr_model._fields.get(db_col)
                    else:
                        field = curr_model._fields.get(part)
                        db_col = part

                if not field or not hasattr(field, "to"):
                    raise ValueError(
                        f"'{part}' (path '{field_name}') xato kiritildi. select_related faqat ForeignKey yoki OneToOne bilan ishlaydi."
                    )

                if isinstance(field, ManyToMany):
                    raise TypeError(
                        f"'{part}' bu ManyToMany! Uning uchun select_related() emas, balki prefetch_related() ishlating."
                    )

                target_model = field.to
                target_table = target_model.table
                rel_path.append(rel_name)
                current_rel_str = "__".join(rel_path)

                join_alias = f"{curr_table_alias}__{rel_name}"
                join_table_expr = f"{target_table} AS {join_alias}"

                on_condition = f"{curr_table_alias}.{db_col} = {join_alias}.{target_model.get_pk_name()}"
                if not any(j[1] == join_table_expr for j in qs._join):
                    qs._join.append(("LEFT JOIN", join_table_expr, on_condition))

                if current_rel_str not in qs._select_related:
                    qs._select_related.append(current_rel_str)

                curr_model = target_model
                curr_table_alias = join_alias

        return qs

    def group_by(self, value):
        qs = self._clone()
        qs._group_by = value
        return qs

    def values(self, *fields):
        qs = self._clone()
        if fields:
            qs._columns = qs._build_values_columns(fields)
        qs._return_type = "dict"
        return qs

    def values_list(self, *fields, flat=False):
        qs = self._clone()
        if fields:
            qs._columns = qs._build_values_columns(fields)
        qs._return_type = "list"
        qs._flat = flat
        return qs

        """
        Faqat ko'rsatilgan ustunlarni yuklaydi (Asinxron). Model obyektlari qaytariladi.
        """
        qs = self._clone()
        if not fields:
            return qs

        pk = self.model.get_pk_name()
        pk_list = [pk] if isinstance(pk, str) else list(pk)

        selected = list(fields)
        for p in pk_list:
            if p not in selected and p in self.model._fields:
                selected.insert(0, p)

        for f in fields:
            if f not in self.model._fields:
                raise ValueError(
                    f"'{f}' ustuni {self.model.__name__} modelida mavjud emas"
                )

        qs._columns = ", ".join(selected)
        return qs

    def defer(self, *fields):
        """
        Ko'rsatilgan ustunlardan tashqari barcha ustunlarni yuklaydi (Asinxron).
        """
        qs = self._clone()
        if not fields:
            return qs

        pk = self.model.get_pk_name()
        pk_set = set([pk] if isinstance(pk, str) else list(pk))
        deferred = set(fields) - pk_set

        selected = [
            f
            for f in self.model._fields
            if f not in deferred and self.model._fields[f].to_sql()
        ]
        qs._columns = ", ".join(selected)
        return qs

    def prefetch_related(self, *fields):
        qs = self._clone()
        if qs._prefetch is None:
            qs._prefetch = []
        qs._prefetch.extend(fields)
        return qs

    def select_for_update(self):
        """
        Joriy tranzaksiya doirasida tanlangan qatorlarni qulflash (lock) uchun.
        Pessimistic locking (balans yangilash va sh.k. poyga holatlarining oldini olish uchun).
        """
        qs = self._clone()
        qs._select_for_update = True
        return qs

    async def all(self):
        where = self._build_where()

        group_by = self._group_by
        if hasattr(self, "_annotations") and self._annotations and not group_by:
            group_by = f"{self.model.table}.{self.model.get_pk_name()}"

        records = await self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=group_by,
            order_by=self._get_order_by_sql(),
            limit=self._limit,
            offset=self._offset,
            fetchone=False,
            for_update=self._select_for_update,
        )

        if getattr(self, "_return_type", None) == "dict":
            return records
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                return [
                    list(r.values())[0] if isinstance(r, dict) else r[0]
                    for r in records
                ]
            return [
                tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in records
            ]

        instances = self._hydrate_records(records)
        res = await self._process_prefetch(instances)
        return res

    async def first(self):
        where = self._build_where()
        records = await self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._get_order_by_sql(),
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=False,
            for_update=self._select_for_update,
        )

        if not records:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return records[0]
        elif getattr(self, "_return_type", None) == "list":
            rec = records[0]
            if getattr(self, "_flat", False):
                return list(rec.values())[0] if isinstance(rec, dict) else rec[0]
            return tuple(rec.values()) if isinstance(rec, dict) else tuple(rec)

        instances = self._hydrate_records(records)
        instances = await self._process_prefetch(instances)
        return instances[0] if instances else None

    async def get_or_create(self, defaults=None, **kwargs):
        qs = self.filter(**kwargs)
        obj = await qs.first()
        if obj:
            return obj, False

        params = kwargs.copy()
        if defaults:
            params.update(defaults)

        return await self.model.create(**params), True

    async def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        qs = self.filter(**kwargs)
        obj = await qs.first()
        if obj:
            for key, value in defaults.items():
                setattr(obj, key, value)
            await obj.save()
            return obj, False

        params = kwargs.copy()
        params.update(defaults)
        return await self.model.create(**params), True

    async def update(self, force: bool = False, **kwargs):
        for name, field in self.model._fields.items():
            if getattr(field, "auto_now", False) and name not in kwargs:
                kwargs[name] = field.get_current_value()
        if not kwargs:
            return 0
        where = self._build_where()
        has_where = where and (not isinstance(where, Q) or where.conditions or where.children)
        if not has_where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy update uchun filter berish shart! (Barcha qatorlarni o'zgartirish uchun force=True yoki .force() ishlating)"
            )
        return await self.model.db.update_where(self.model.table, kwargs, where=where)

    async def delete(self, force: bool = False):
        where = self._build_where()
        has_where = where and (not isinstance(where, Q) or where.conditions or where.children)
        if not has_where and not (force or getattr(self, "_force", False)):
            raise ValueError(
                "Ommaviy delete uchun filter berish shart! (Barcha qatorlarni o'chirish uchun force=True yoki .force() ishlating)"
            )
        return await self.model.db.delete_where(self.model.table, where=where)

    async def last(self):
        where = self._build_where()

        records = await self.model.db.select(
            self.model.table,
            columns=self._get_columns_sql(),
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._get_reverse_order_by_sql(),
            limit=1,
            offset=self._offset,
            fetchone=False,
            for_update=self._select_for_update,
        )

        if not records:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return records[0]
        elif getattr(self, "_return_type", None) == "list":
            rec = records[0]
            if getattr(self, "_flat", False):
                return list(rec.values())[0] if isinstance(rec, dict) else rec[0]
            return tuple(rec.values()) if isinstance(rec, dict) else tuple(rec)

        instances = self._hydrate_records(records)
        instances = await self._process_prefetch(instances)
        return instances[0] if instances else None

    async def count(self):
        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns="COUNT(*)",
            where=where,
            join=self._join,
            fetchone=True,
        )
        if hasattr(record, "items"):
            return list(record.values())[0]
        return record[0] if record else 0

    async def aggregate(self, **kwargs):
        columns = []
        for alias, agg in kwargs.items():
            columns.append(f"{agg.to_sql()} AS {alias}")

        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns=", ".join(columns),
            where=where,
            join=self._join,
            fetchone=True,
        )
        return dict(record) if record else {}

    async def exists(self):
        where = self._build_where()
        return await self.model.db.exists_where(
            self.model.table,
            where=where,
            join=self._join,
            group_by=self._group_by,
        )

    def _get_order_by_sql(self):
        order_by = self._order_by
        if not order_by:
            order_by = self.model._meta_options.get("ordering", None)

        if not order_by:
            return None

        if isinstance(order_by, str):
            order_by = [order_by]

        parts = []
        for item in order_by:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if item.startswith("-"):
                col = item[1:].strip()
                direction = "DESC"
            else:
                col = item.strip()
                direction = "ASC"

            if "." not in col:
                col = f"{self.model.table}.{col}"

            parts.append(f"{col} {direction}")
        return ", ".join(parts) if parts else None

    def _get_reverse_order_by_sql(self):
        order_sql = self._get_order_by_sql()
        if not order_sql:
            pk_name = self.model.get_pk_name()
            return f"{self.model.table}.{pk_name} DESC"

        parts = []
        for part in order_sql.split(","):
            part = part.strip()
            if part.endswith(" DESC"):
                parts.append(part[:-5] + " ASC")
            elif part.endswith(" ASC"):
                parts.append(part[:-4] + " DESC")
            else:
                parts.append(part + " DESC")
        return ", ".join(parts)

    def _build_where(self):
        from postgresdb3.orm.expressions import Q

        final_q = Q()

        if self._where:
            if isinstance(self._where, dict):
                final_q &= Q(**self._where)
            elif isinstance(self._where, list):
                for w in self._where:
                    if isinstance(w, Q):
                        final_q &= w
                    elif isinstance(w, dict):
                        final_q &= Q(**w)

        if self._exclude:
            if isinstance(self._exclude, dict):
                final_q &= ~Q(**self._exclude)
            elif isinstance(self._exclude, list):
                for e in self._exclude:
                    if isinstance(e, Q):
                        final_q &= ~e
                    elif isinstance(e, dict):
                        final_q &= ~Q(**e)

        return final_q if (final_q.conditions or final_q.children) else None


class FindQuerySet(QuerySet):
    """
    Model.find(pk) orqali qaytariladigan so'rov obyekti.
    To'g'ridan-to'g'ri update/delete chaqirish ham, model atributlariga murojaat qilish ham mumkin.
    """

    def __init__(self, model, pk_value):
        super().__init__(model)
        self.pk_value = pk_value
        self._where = [{model.get_pk_name(): pk_value}]
        self._instance = None
        self._fetched = False

    def _get_instance(self):
        if not self._fetched:
            self._instance = self.first()
            self._fetched = True
        return self._instance

    def update(self, **kwargs):
        res = super().update(**kwargs)
        self._fetched = False
        return res

    def delete(self):
        res = super().delete()
        self._fetched = False
        return res

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        inst = self._get_instance()
        if inst is None:
            raise AttributeError(
                f"'{self.model.__name__}' object with {self.model.get_pk_name()}={self.pk_value} not found"
            )
        return getattr(inst, name)

    def __bool__(self):
        return self._get_instance() is not None

    def __repr__(self):
        inst = self._get_instance()
        return repr(inst) if inst is not None else f"<{self.model.__name__}: None>"

    def __eq__(self, other):
        if other is None:
            return self._get_instance() is None
        inst = self._get_instance()
        if inst is None:
            return False
        return inst == other


class AsyncFindQuerySet(AsyncQuerySet):
    """
    AsyncModel.find(pk) orqali qaytariladigan asinxron so'rov obyekti.
    await AsyncModel.find(pk) -> Model obyekti qaytaradi.
    await AsyncModel.find(pk).update(...) -> yangilaydi.
    await AsyncModel.find(pk).delete() -> o'chiradi.
    """

    def __init__(self, model, pk_value):
        super().__init__(model)
        self.pk_value = pk_value
        self._where = [{model.get_pk_name(): pk_value}]

    def __await__(self):
        return self.first().__await__()

    async def update(self, **kwargs):
        return await super().update(**kwargs)

    async def delete(self):
        return await super().delete()
