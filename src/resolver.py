from semver import Version, Constraint


class ResolutionError(Exception):
    pass


class Resolver:
    def __init__(self, registry):
        self.registry = registry

    def resolve(self, root_dependencies):
        constraints = {}
        for name, spec in root_dependencies.items():
            constraints.setdefault(name, []).append(("<root>", Constraint(spec)))

        resolved = {}
        changed = True
        while changed:
            changed = False
            for name in list(constraints.keys()):
                chosen = self._choose(name, constraints[name])
                if resolved.get(name) == chosen:
                    continue
                resolved[name] = chosen
                changed = True
                deps = self.registry.dependencies_of(name, chosen)
                for dep_name, dep_spec in deps.items():
                    self._add_constraint(constraints, dep_name, name, dep_spec)
        return resolved

    def _add_constraint(self, constraints, name, source, spec):
        entry = (source, Constraint(spec))
        existing = constraints.setdefault(name, [])
        for src, con in existing:
            if src == source and str(con) == str(entry[1]):
                return
        existing.append(entry)

    def _choose(self, name, constraint_list):
        if not self.registry.exists(name):
            raise ResolutionError(f"package '{name}' not found in registry")
        available = self.registry.versions(name)
        candidates = list(available)
        for _source, constraint in constraint_list:
            candidates = [v for v in candidates if constraint.matches(v)]
        if not candidates:
            reqs = ", ".join(f"{src} requires {c}" for src, c in constraint_list)
            raise ResolutionError(
                f"no version of '{name}' satisfies all constraints ({reqs}); "
                f"available: {', '.join(str(v) for v in sorted(available))}"
            )
        return max(candidates)


def resolve_dependencies(registry, root_dependencies):
    return Resolver(registry).resolve(root_dependencies)
