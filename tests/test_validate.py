from __future__ import annotations

import pytest

from compose_stacks.catalog import Stack
from compose_stacks.validate import RULES, Report, looks_secret, validate_stack
from conftest import COMPOSE, ENV_EXAMPLE, README, STACK_TOML, write_stack


def codes(path) -> set[str]:
    return {i.code for i in validate_stack(Stack.load(path)).issues}


def test_valid_stack_is_clean(demo_stack):
    report = validate_stack(Stack.load(demo_stack))
    assert report.issues == []
    assert report.ok(strict=True)
    assert report.checked == ["demo"]


def test_missing_files(stacks_root):
    path = write_stack(stacks_root, compose=None, readme=None)
    assert "CS001" in codes(path)


def test_unparseable_toml(stacks_root):
    path = write_stack(stacks_root, toml="name = ")
    assert "CS002" in codes(path)


def test_schema_problem_and_name_mismatch(stacks_root):
    toml = STACK_TOML.replace('category = "devtools"', 'category = "unknown"')
    path = write_stack(stacks_root, name="other", toml=toml)
    found = codes(path)
    assert {"CS003", "CS004"} <= found


def test_readme_sections(stacks_root):
    path = write_stack(stacks_root, readme="# Demo\n\nNothing here.\n")
    report = validate_stack(Stack.load(path))
    assert [i.code for i in report.issues] == ["CS005", "CS005"]
    assert report.ok() and not report.ok(strict=True)


def test_invalid_compose(stacks_root):
    path = write_stack(stacks_root, compose="services: [")
    assert "CS010" in codes(path)


def test_service_not_mapping(stacks_root):
    path = write_stack(stacks_root, compose=COMPOSE.replace("services:\n  app:", "services:\n  junk: 1\n  app:"))
    assert "CS010" in codes(path)


def test_obsolete_version_key(stacks_root):
    path = write_stack(stacks_root, compose='version: "3.8"\n' + COMPOSE)
    assert "CS011" in codes(path)


def test_build_not_allowed(stacks_root):
    path = write_stack(stacks_root, compose=COMPOSE.replace("image: example/app:1.2.3", "build: ."))
    assert "CS012" in codes(path)


@pytest.mark.parametrize("image", ["example/app", "example/app:latest", "example/app:main"])
def test_unpinned_images(stacks_root, image):
    path = write_stack(stacks_root, compose=COMPOSE.replace("example/app:1.2.3", image))
    assert "CS013" in codes(path)


def test_unpinned_image_via_variable(stacks_root):
    compose = COMPOSE.replace("example/app:1.2.3", "example/app:${APP_TAG:-latest}")
    path = write_stack(stacks_root, compose=compose)
    assert "CS013" in codes(path)


def test_digest_counts_as_pinned(stacks_root):
    path = write_stack(stacks_root, compose=COMPOSE.replace("example/app:1.2.3", "example/app@sha256:" + "a" * 64))
    assert "CS013" not in codes(path)


def test_major_only_tag_warning(stacks_root):
    path = write_stack(stacks_root, compose=COMPOSE.replace("example/app:1.2.3", "example/app:18-alpine"))
    assert "CS014" in codes(path)


def test_missing_healthcheck(stacks_root):
    compose = COMPOSE.replace('    healthcheck:\n      test: ["CMD", "true"]\n', "")
    path = write_stack(stacks_root, compose=compose)
    assert {"CS015", "CS016"} <= codes(path)


def test_healthcheck_exemption(stacks_root):
    compose = COMPOSE.replace('    healthcheck:\n      test: ["CMD", "true"]\n', "")
    toml = STACK_TOML.replace(
        '[healthcheck]\nservices = ["app"]', '[healthcheck]\nexempt = { app = "Image has no shell or HTTP client" }'
    )
    path = write_stack(stacks_root, compose=compose, toml=toml)
    assert codes(path) == set()


def test_healthcheck_metadata_mismatches(stacks_root):
    toml = STACK_TOML.replace('services = ["app"]', 'services = ["ghost"]\nexempt = { other = "A long enough reason" }')
    path = write_stack(stacks_root, toml=toml)
    messages = [i.message for i in validate_stack(Stack.load(path)).issues if i.code == "CS016"]
    assert any("unknown service 'ghost'" in m for m in messages)
    assert any("add 'app' to healthcheck.services" in m for m in messages)
    assert any("exempt lists unknown service 'other'" in m for m in messages)


def test_exempt_service_that_has_healthcheck_warns(stacks_root):
    toml = STACK_TOML.replace('services = ["app"]', 'services = ["app"]\nexempt = { app = "A long enough reason" }')
    report = validate_stack(Stack.load(write_stack(stacks_root, toml=toml)))
    assert any(i.code == "CS016" and i.level == "warning" for i in report.issues)


def test_restart_container_name_privileged(stacks_root):
    compose = COMPOSE.replace("    restart: unless-stopped\n", "    container_name: app\n    privileged: true\n")
    assert {"CS017", "CS018", "CS019"} <= codes(write_stack(stacks_root, compose=compose))


def test_invalid_port(stacks_root):
    compose = COMPOSE.replace('"${BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}:80"', '"not-a-port"')
    assert "CS020" in codes(write_stack(stacks_root, compose=compose))


def test_random_host_port_warning(stacks_root):
    compose = COMPOSE.replace('"${BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}:80"', '"80"')
    report = validate_stack(Stack.load(write_stack(stacks_root, compose=compose)))
    assert any(i.code == "CS020" and i.level == "warning" for i in report.issues)


def test_public_binding_needs_declaration(stacks_root):
    compose = COMPOSE.replace('"${BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}:80"', '"${APP_PORT:-8080}:80"')
    env = ENV_EXAMPLE.replace("BIND_ADDRESS=127.0.0.1\n", "")
    toml = STACK_TOML.replace('[env.BIND_ADDRESS]\ndescription = "Bind address"\ndefault = "127.0.0.1"\n', "")
    path = write_stack(stacks_root, compose=compose, env=env, toml=toml)
    assert codes(path) == {"CS021"}
    toml_public = toml.replace("container = 80\n", 'container = 80\nbind = "0.0.0.0"\n')
    path = write_stack(stacks_root, compose=compose, env=env, toml=toml_public)
    assert codes(path) == set()


def test_declared_public_but_bound_locally(stacks_root):
    toml = STACK_TOML.replace("container = 80\n", 'container = 80\nbind = "0.0.0.0"\n')
    assert "CS021" in codes(write_stack(stacks_root, toml=toml))


def test_bind_address_mismatch(stacks_root):
    toml = STACK_TOML.replace("container = 80\n", 'container = 80\nbind = "10.0.0.5"\n')
    assert "CS021" in codes(write_stack(stacks_root, toml=toml))


def test_port_documentation_mismatch(stacks_root):
    toml = STACK_TOML.replace("host = 8080", "host = 9999")
    report = validate_stack(Stack.load(write_stack(stacks_root, toml=toml)))
    cs022 = [i.message for i in report.issues if i.code == "CS022"]
    assert len(cs022) == 2


def test_volumes_documentation(stacks_root):
    toml = STACK_TOML.replace('name = "app_data"', 'name = "other_data"')
    assert {"CS030", "CS031"} <= codes(write_stack(stacks_root, toml=toml))


def test_undefined_variable(stacks_root):
    compose = COMPOSE.replace(
        "APP_SECRET: ${APP_SECRET:?required}", "APP_SECRET: ${APP_SECRET:?required}\n      X: ${UNDEFINED}"
    )
    assert "CS040" in codes(write_stack(stacks_root, compose=compose))


def test_variable_with_default_is_fine(stacks_root):
    compose = COMPOSE.replace(
        "APP_SECRET: ${APP_SECRET:?required}", "APP_SECRET: ${APP_SECRET:?required}\n      X: ${OPTIONAL:-1}"
    )
    assert "CS040" not in codes(write_stack(stacks_root, compose=compose))


def test_env_var_missing_from_example(stacks_root):
    env = ENV_EXAMPLE.replace("APP_SECRET=\n", "")
    assert {"CS040", "CS041"} <= codes(write_stack(stacks_root, env=env))


def test_secret_with_value_in_example(stacks_root):
    env = ENV_EXAMPLE.replace("APP_SECRET=\n", "APP_SECRET=hunter2hunter2\n")
    assert "CS042" in codes(write_stack(stacks_root, env=env))


def test_hardcoded_secret_in_compose(stacks_root):
    compose = COMPOSE.replace(
        "APP_SECRET: ${APP_SECRET:?required}", "APP_SECRET: ${APP_SECRET:?required}\n      DB_PASSWORD: literal"
    )
    assert "CS043" in codes(write_stack(stacks_root, compose=compose))


def test_list_style_environment_hardcoded_secret(stacks_root):
    compose = COMPOSE.replace(
        "    environment:\n      APP_SECRET: ${APP_SECRET:?required}\n",
        "    environment:\n"
        "      - APP_SECRET=${APP_SECRET:?required}\n"
        "      - API_TOKEN=abc123def\n"
        "      - USE_PASSWORD=true\n",
    )
    report = validate_stack(Stack.load(write_stack(stacks_root, compose=compose)))
    assert [i.message for i in report.issues if i.code == "CS043"] == [
        "service 'app' sets API_TOKEN to a literal value"
    ]


def test_credential_patterns(stacks_root):
    fake_key = "AKIA" + "Q" * 16
    url_with_password = "postgres://" + "admin" + ":" + "hunter22" + "@db/app"
    readme = README + f"\nexample: {fake_key}\n{url_with_password}\n"
    report = validate_stack(Stack.load(write_stack(stacks_root, readme=readme)))
    messages = [i.message for i in report.issues if i.code == "CS044"]
    assert any("AWS access key id" in m for m in messages)
    assert any("credentials in a URL" in m for m in messages)


def test_credentials_in_url_with_variables_are_fine(stacks_root):
    readme = README + "\npostgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/app\n"
    assert "CS044" not in codes(write_stack(stacks_root, readme=readme))


def test_private_key_detected_in_extra_file(stacks_root):
    path = write_stack(stacks_root)
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    (path / "config").mkdir()
    (path / "config" / "key.conf").write_text(header + "\n", encoding="utf-8")
    assert "CS044" in codes(path)


def test_env_not_described_missing_hint_and_secret_lookalike(stacks_root):
    env = ENV_EXAMPLE.replace("# Generate: openssl rand -hex 32\n", "") + "EXTRA=1\n"
    toml = STACK_TOML + '\n[env.SESSION_TOKEN]\ndescription = "x"\n'
    env += "SESSION_TOKEN=\n"
    found = codes(write_stack(stacks_root, env=env, toml=toml))
    assert {"CS045", "CS046", "CS047"} <= found


def test_default_mismatch(stacks_root):
    toml = STACK_TOML.replace('default = "8080"', 'default = "9090"')
    assert "CS048" in codes(write_stack(stacks_root, toml=toml))


def test_looks_secret():
    assert looks_secret("POSTGRES_PASSWORD")
    assert looks_secret("N8N_ENCRYPTION_KEY")
    assert looks_secret("api_token")
    assert not looks_secret("POSTGRES_PASSWORD_FILE")
    assert not looks_secret("POSTGRES_USER")
    assert not looks_secret("KEYBOARD_LAYOUT")


def test_report_helpers():
    report = Report(checked=["a"])
    report.add("CS005", "a", "warn")
    report.add("CS001", "a", "err")
    assert len(report.errors) == 1 and len(report.warnings) == 1
    data = report.to_dict()
    assert data["errors"] == 1 and data["warnings"] == 1 and len(data["issues"]) == 2


def test_rule_table_is_consistent():
    assert all(code.startswith("CS") and len(code) == 5 for code in RULES)
    assert all(level in ("error", "warning", "info") for level, _ in RULES.values())
