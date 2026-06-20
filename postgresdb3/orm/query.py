from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')

@dataclass
class PaginationResult(Generic[T]):
    total: int
    pages: int
    current_page: int
    per_page: int
    has_next: bool
    has_prev: bool
    data: list[T]

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

    def _clone(self):
        qs = self.__class__(self.model)
        qs._where = dict(self._where) if self._where else None
        qs._exclude = dict(self._exclude) if self._exclude else None
        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = self._join
        qs._group_by = self._group_by
        return qs

    def update(self, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(f"{self.model.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where:
            raise ValueError("Yangilash uchun shart berilishi kerak")

        return self.model.db.update_where(
            self.model.table,
            kwargs,
            where
        )

    def delete(self):
        self.model._check_setup()

        where = self._build_where()

        if not where:
            raise ValueError("O'chirish uchun shart berilishi kerak")

        return self.model.db.delete_where(
            self.model.table,
            where
        )

    def join(self, table, on_condition, join_type="INNER JOIN"):
        qs = self._clone()
        if qs._join is None:
            qs._join = []
        qs._join.append((join_type, table, on_condition))
        return qs

    def select_related(self, *fields):
        """
        N+1 muammosini oldini olish uchun yozilgan metod.
        Berilgan ForeignKey maydonlari bo'yicha avtomatik JOIN qiladi.
        """
        qs = self._clone()
        if qs._join is None:
            qs._join = []
            
        for field_name in fields:
            field = self.model._fields.get(field_name)
            if not field or not hasattr(field, "to"):
                raise ValueError(f"'{field_name}' xato kiritildi. select_related faqat ForeignKey yoki OneToOneField bilan ishlaydi.")
                
            from .fields.foreign import ManyToManyField
            if isinstance(field, ManyToManyField):
                raise TypeError(f"'{field_name}' bu ManyToManyField! Uning uchun select_related() emas, balki prefetch_related() ishlating.")
                
            related_table = field.to.table
            on_condition = f"{self.model.table}.{field_name} = {related_table}.{field.to.get_pk_name()}"
            qs._join.append(("LEFT JOIN", related_table, on_condition))
            
        return qs

    def prefetch_related(self, *fields):
        """
        Ko'pga-ko'p (ManyToMany) va Birga-ko'p (OneToMany) bog'lanishlar uchun N+1 muammosini oldini olish.
        Ushbu metod ma'lumotlarni alohida so'rovlar orqali olib, xotirada bog'lab qo'yadi.
        """
        qs = self._clone()
        if not hasattr(qs, "_prefetch"):
            qs._prefetch = []
        qs._prefetch.extend(fields)
        return qs

    def _process_auto_joins(self, kwargs):
        new_kwargs = {}
        for key, value in kwargs.items():
            parts = key.split("__")
            
            if len(parts) >= 2:
                field_name = parts[0]
                relation = getattr(self.model, field_name, None)
                
                if relation and hasattr(relation, "related_model"):
                    target_table = relation.related_model.table
                    source_col = getattr(relation, "field_name", field_name)
                    target_col = relation.related_model.get_pk_name()
                    
                    join_condition = f"{self.model.table}.{source_col} = {target_table}.{target_col}"
                    
                    if not self._join:
                        self._join = []
                        
                    join_exists = any(
                        j[1] == target_table and j[2] == join_condition 
                        for j in self._join if isinstance(j, tuple) and len(j) == 3
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
            qs._where.append(arg)

        if kwargs:
            qs._where.append(qs._process_auto_joins(kwargs))

        return qs

    def exclude(self, **kwargs):
        qs = self._clone()

        if not kwargs:
            return qs

        if qs._exclude is None:
            qs._exclude = {}

        qs._exclude.update(qs._process_auto_joins(kwargs))
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
            qs._columns = ", ".join(fields)
        qs._return_type = "dict"
        return qs

    def values_list(self, *fields, flat=False):
        qs = self._clone()
        if fields:
            qs._columns = ", ".join(fields)
        qs._return_type = "list"
        qs._flat = flat
        return qs

    def all(self):
        where = self._build_where()
        
        columns = self._columns or "*"
        group_by = self._group_by
        
        if hasattr(self, "_annotations") and self._annotations:
            if columns == "*":
                columns = f"{self.model.table}.*"
            for alias, expression in self._annotations.items():
                if hasattr(expression, "to_sql"):
                    columns += f", {expression.to_sql()} AS {alias}"
                else:
                    columns += f", {expression} AS {alias}"
            
            if not group_by:
                group_by = f"{self.model.table}.{self.model.get_pk_name()}"

        records = self.model.db.select(
            self.model.table,
            columns=columns,
            where=where,
            join=self._join,
            group_by=group_by,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
        )
        
        if getattr(self, "_return_type", None) == "dict":
            return records
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                return [list(r.values())[0] if isinstance(r, dict) else r[0] for r in records]
            return [tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in records]
            
        instances = self.model._from_records(records)
        
                                            
        if hasattr(self, "_prefetch") and self._prefetch and instances:
            for field_name in self._prefetch:
                relation = getattr(self.model, field_name, None)
                if not relation:
                    continue
                
                pk_name = self.model.get_pk_name()
                instance_pks = [getattr(inst, pk_name) for inst in instances]
                
                                                  
                from postgresdb3.orm.relations import ManyToManyRelation, ReverseRelation
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
                        target_instances = target_model.filter(**{f"{target_model.get_pk_name()}__in": list(target_ids)}).all()
                        target_map = {getattr(t, target_model.get_pk_name()): t for t in target_instances}
                        
                        for inst in instances:
                            pk = getattr(inst, pk_name)
                            prefetched = [target_map[t_id] for t_id in mapping_dict.get(pk, []) if t_id in target_map]
                            setattr(inst, f"_prefetched_{field_name}", prefetched)
                            
                elif isinstance(relation, ReverseRelation):
                    related_model = relation.related_model
                    fk_name = relation.fk_name
                    
                    related_instances = related_model.filter(**{f"{fk_name}__in": instance_pks}).all()
                    
                    for inst in instances:
                        pk = getattr(inst, pk_name)
                        prefetched = [r for r in related_instances if getattr(r, fk_name) == pk]
                        setattr(inst, f"_prefetched_{field_name}", prefetched)
        
        return instances

    def first(self):
        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True,
        )
        return self.model._from_record(record)

    def last(self):
        pk_name = self.model.get_pk_name()

        order = self._order_by
        if not order:
            order = f"-{pk_name}"
        elif isinstance(order, str):
            if order.startswith("-"):
                order = order[1:]
            else:
                order = f"-{order}"

        where = self._build_where()

        record = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=order,
            limit=1,
            offset=self._offset,
            fetchone=True,
        )

        if not record:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return record
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                return list(record.values())[0] if isinstance(record, dict) else record[0]
            return tuple(record.values()) if isinstance(record, dict) else tuple(record)

        return self.model._from_record(record)

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

    def update(self, **kwargs):
        if not kwargs:
            return 0
        where = self._build_where()
        if not where:
            raise ValueError("Ommaviy update uchun filter berish shart! (Barcha qatorlarni o'zgartirishdan himoya)")
        return self.model.db.update_where(self.model.table, kwargs, where=self._where)

    def delete(self):
        where = self._build_where()
        if not where:
            raise ValueError("Ommaviy delete uchun filter berish shart! (Barcha qatorlarni o'chirishdan himoya)")
        return self.model.db.delete_where(self.model.table, where=self._where)

    def count(self):
        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns="COUNT(*)",
            where=where,
            join=self._join,
            fetchone=True
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
            fetchone=True
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
            data=data
        )

    def exists(self):
        where = self._build_where()
        return self.model.db.exists_where(
            self.model.table,
            where=where,
            join=self._join,
            group_by=self._group_by,
        )

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

    def _clone(self):
        qs = self.__class__(self.model)
        qs._where = dict(self._where) if self._where else None
        qs._exclude = dict(self._exclude) if self._exclude else None
        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = self._join
        qs._group_by = self._group_by
        return qs

    async def update(self, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(f"{self.model.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where:
            raise ValueError("Yangilash uchun shart berilishi kerak")

        return await self.model.db.update_where(
            self.model.table,
            kwargs,
            where
        )

    async def delete(self):
        self.model._check_setup()

        where = self._build_where()

        if not where:
            raise ValueError("O'chirish uchun shart berilishi kerak")

        return await self.model.db.delete_where(
            self.model.table,
            where
        )

    def _process_auto_joins(self, kwargs):
        new_kwargs = {}
        for key, value in kwargs.items():
            parts = key.split("__")
            
            if len(parts) >= 2:
                field_name = parts[0]
                relation = getattr(self.model, field_name, None)
                
                if relation and hasattr(relation, "related_model"):
                    target_table = relation.related_model.table
                    source_col = getattr(relation, "field_name", field_name)
                    target_col = relation.related_model.get_pk_name()
                    
                    join_condition = f"{self.model.table}.{source_col} = {target_table}.{target_col}"
                    
                    if not self._join:
                        self._join = []
                        
                    join_exists = any(
                        j[1] == target_table and j[2] == join_condition 
                        for j in self._join if isinstance(j, tuple) and len(j) == 3
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

        qs._where.extend(args)
        if kwargs:
            qs._where.append(qs._process_auto_joins(kwargs))
        return qs

    def annotate(self, **kwargs):
        qs = self._clone()
        if not hasattr(qs, "_annotations"):
            qs._annotations = {}
        qs._annotations.update(kwargs)
        return qs

    def paginate(self, page: int = 1, per_page: int = 10):
        total = self.count()
        offset = (page - 1) * per_page
        data = self.limit(per_page).offset(offset).all()
        import math
        return {
            "data": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if per_page else 1
        }

    def exclude(self, *args, **kwargs):
        qs = self._clone()

        if qs._exclude is None:
            qs._exclude = []
            
        if not isinstance(qs._exclude, list):
            qs._exclude = [qs._exclude]

        qs._exclude.extend(args)
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

    def join(self, table, on_condition, join_type="INNER JOIN"):
        qs = self._clone()
        if qs._join is None:
            qs._join = []
        qs._join.append((join_type, table, on_condition))
        return qs

    def select_related(self, *fields):
        """
        N+1 muammosini oldini olish uchun yozilgan asinxron metod.
        Berilgan ForeignKey maydonlari bo'yicha avtomatik JOIN qiladi.
        """
        qs = self._clone()
        if qs._join is None:
            qs._join = []
            
        for field_name in fields:
            field = self.model._fields.get(field_name)
            if not field or not hasattr(field, "to"):
                raise ValueError(f"'{field_name}' xato kiritildi. select_related faqat ForeignKey yoki OneToOneField bilan ishlaydi.")
                
            from .fields.foreign import ManyToManyField
            if isinstance(field, ManyToManyField):
                raise TypeError(f"'{field_name}' bu ManyToManyField! Uning uchun select_related() emas, balki prefetch_related() ishlating.")
                
            related_table = field.to.table
            on_condition = f"{self.model.table}.{field_name} = {related_table}.{field.to.get_pk_name()}"
            qs._join.append(("LEFT JOIN", related_table, on_condition))
            
        return qs

    def group_by(self, value):
        qs = self._clone()
        qs._group_by = value
        return qs

    def values(self, *fields):
        qs = self._clone()
        if fields:
            qs._columns = ", ".join(fields)
        qs._return_type = "dict"
        return qs

    def values_list(self, *fields, flat=False):
        qs = self._clone()
        if fields:
            qs._columns = ", ".join(fields)
        qs._return_type = "list"
        qs._flat = flat
        return qs

    def prefetch_related(self, *fields):
        qs = self._clone()
        if not hasattr(qs, "_prefetch"):
            qs._prefetch = []
        qs._prefetch.extend(fields)
        return qs

    async def all(self):
        where = self._build_where()
        
        columns = self._columns or "*"
        group_by = self._group_by
        
        if hasattr(self, "_annotations") and self._annotations:
            if columns == "*":
                columns = f"{self.model.table}.*"
            for alias, expression in self._annotations.items():
                if hasattr(expression, "to_sql"):
                    columns += f", {expression.to_sql()} AS {alias}"
                else:
                    columns += f", {expression} AS {alias}"
            
            if not group_by:
                group_by = f"{self.model.table}.{self.model.get_pk_name()}"

        records = await self.model.db.select(
            self.model.table,
            columns=columns,
            where=where,
            join=self._join,
            group_by=group_by,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            fetchone=False,
        )
        
        if getattr(self, "_return_type", None) == "dict":
            return records
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                return [list(r.values())[0] if isinstance(r, dict) else r[0] for r in records]
            return [tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in records]
            
        instances = self.model._from_records(records)
        
        if hasattr(self, "_prefetch") and self._prefetch and instances:
            for field_name in self._prefetch:
                relation = getattr(self.model, field_name, None)
                if not relation:
                    continue
                
                pk_name = self.model.get_pk_name()
                instance_pks = [getattr(inst, pk_name) for inst in instances]
                
                from postgresdb3.orm.relations import ManyToManyRelation, AsyncReverseRelation
                if isinstance(relation, ManyToManyRelation):
                    target_model = relation.target_model
                    through_table = relation.through_table
                    source_col = relation.source_col
                    target_col = relation.target_col
                    
                    placeholders = ", ".join([f"${i+1}" for i in range(len(instance_pks))])
                    sql = f"SELECT {source_col}, {target_col} FROM {through_table} WHERE {source_col} IN ({placeholders})"
                    
                    mapping_records = await self.model.db._manager(sql, *instance_pks, fetchall=True)
                    
                    mapping_dict = {}
                    target_ids = set()
                    for r in mapping_records:
                        s_id, t_id = r[source_col], r[target_col]
                        if s_id not in mapping_dict:
                            mapping_dict[s_id] = []
                        mapping_dict[s_id].append(t_id)
                        target_ids.add(t_id)
                        
                    if target_ids:
                        target_instances = await target_model.filter(**{f"{target_model.get_pk_name()}__in": list(target_ids)}).all()
                        target_map = {getattr(t, target_model.get_pk_name()): t for t in target_instances}
                        
                        for inst in instances:
                            pk = getattr(inst, pk_name)
                            prefetched = [target_map[t_id] for t_id in mapping_dict.get(pk, []) if t_id in target_map]
                            setattr(inst, f"_prefetched_{field_name}", prefetched)
                            
                elif isinstance(relation, AsyncReverseRelation):
                    related_model = relation.related_model
                    fk_name = relation.fk_name
                    
                    related_instances = await related_model.filter(**{f"{fk_name}__in": instance_pks}).all()
                    
                    for inst in instances:
                        pk = getattr(inst, pk_name)
                        prefetched = [r for r in related_instances if getattr(r, fk_name) == pk]
                        setattr(inst, f"_prefetched_{field_name}", prefetched)
        
        return instances

    async def first(self):
        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True,
        )

        if not record:
            return None

        if getattr(self, "_return_type", None) == "dict":
            return record
        elif getattr(self, "_return_type", None) == "list":
            if getattr(self, "_flat", False):
                return list(record.values())[0] if isinstance(record, dict) else record[0]
            return tuple(record.values()) if isinstance(record, dict) else tuple(record)

        return self.model._from_record(record)

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

    async def update(self, **kwargs):
        if not kwargs:
            return 0
        where = self._build_where()
        if not where:
            raise ValueError("Ommaviy update uchun filter berish shart! (Barcha qatorlarni o'zgartirishdan himoya)")
        return await self.model.db.update_where(self.model.table, kwargs, where=self._where)

    async def delete(self):
        where = self._build_where()
        if not where:
            raise ValueError("Ommaviy delete uchun filter berish shart! (Barcha qatorlarni o'chirishdan himoya)")
        return await self.model.db.delete_where(self.model.table, where=self._where)

    async def last(self):
        pk_name = self.model.get_pk_name()

        order = self._order_by
        if not order:
            order = f"-{pk_name}"
        elif isinstance(order, str):
            if order.startswith("-"):
                order = order[1:]
            else:
                order = f"-{order}"

        where = self._build_where()

        record = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=order,
            limit=1,
            offset=self._offset,
            fetchone=True,
        )

        return self.model._from_record(record)

    async def count(self):
        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns="COUNT(*)",
            where=where,
            join=self._join,
            fetchone=True
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
            fetchone=True
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
