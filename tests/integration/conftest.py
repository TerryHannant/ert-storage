import pytest
import subprocess
import time


@pytest.fixture()
def base_url():
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def auth():
    return "secretSquirrel"


@pytest.fixture(scope="session")
def server(auth):
    server_proc = subprocess.Popen(
        [
            "env",
            f"ERT_STORAGE_TOKEN={auth}",
            "python",
            "-m",
            "ert_storage",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Using a sleep to wait for server start is too fragile, but not much
    # other choice that is lightweight
    time.sleep(30)
    # Check it started successfully
    assert not server_proc.poll(), server_proc.stdout.read().decode("utf-8")
    yield server_proc
    # Shut it down at the end of the pytest session
    server_proc.terminate()


@pytest.fixture
def client(ert_storage_client, monkeypatch):
    """
    Simple rename of ert_storage_client -> client, with security off
    """
    monkeypatch.setenv("ERT_STORAGE_NO_TOKEN", "1")
    return ert_storage_client


@pytest.fixture
def create_ensemble(client):
    def func(
        experiment_id,
        parameters=None,
        responses=None,
        update_id=None,
        active_realizations=None,
        size=-1,
    ):
        if parameters is None:
            parameters = []
        if responses is None:
            responses = []
        if active_realizations is None:
            active_realizations = []
        resp = client.post(
            f"/experiments/{experiment_id}/ensembles",
            json={
                "parameter_names": parameters,
                "response_names": responses,
                "update_id": update_id,
                "size": size,
                "active_realizations": active_realizations,
            },
        )
        return str(resp.json()["id"])

    return func


@pytest.fixture
def create_experiment(client):
    def func(name, priors={}):
        resp = client.post("/experiments", json={"name": name, "priors": priors})
        return resp.json()["id"]

    return func


@pytest.fixture
def simple_ensemble(create_ensemble, create_experiment, request):
    def func(
        parameters=None,
        responses=None,
        update_id=None,
        active_realizations=None,
        size=-1,
    ):
        exp_id = create_experiment(request.node.name)
        ens_id = create_ensemble(
            exp_id, parameters, responses, update_id, active_realizations, size
        )
        return ens_id

    return func


from random import random, choices
from ert_storage.json_schema import prior


def make_const_prior() -> prior.PriorConst:
    return prior.PriorConst(value=random())


def make_trig_prior() -> prior.PriorTrig:
    return prior.PriorTrig(min=random(), max=random(), mode=random())


def make_normal_prior() -> prior.PriorNormal:
    return prior.PriorNormal(mean=random(), std=random())


def make_lognormal_prior() -> prior.PriorLogNormal:
    return prior.PriorLogNormal(mean=random(), std=random())


def make_truncnormal_prior() -> prior.PriorErtTruncNormal:
    return prior.PriorErtTruncNormal(
        mean=random(), std=random(), min=random(), max=random()
    )


def make_stdnormal_prior() -> prior.PriorStdNormal:
    return prior.PriorStdNormal()


def make_uniform_prior() -> prior.PriorUniform:
    return prior.PriorUniform(min=random(), max=random())


def make_duniform_prior() -> prior.PriorErtDUniform:
    return prior.PriorErtDUniform(bins=random(), min=random(), max=random())


def make_loguniform_prior() -> prior.PriorLogUniform:
    return prior.PriorLogUniform(min=random(), max=random())


def make_erf_prior() -> prior.PriorErtErf:
    return prior.PriorErtErf(
        min=random(), max=random(), skewness=random(), width=random()
    )


def make_derf_prior() -> prior.PriorErtDErf:
    return prior.PriorErtDErf(
        bins=random(), min=random(), max=random(), skewness=random(), width=random()
    )


MAKE_PRIOR = [
    make_const_prior,
    make_trig_prior,
    make_normal_prior,
    make_lognormal_prior,
    make_truncnormal_prior,
    make_stdnormal_prior,
    make_uniform_prior,
    make_duniform_prior,
    make_loguniform_prior,
    make_erf_prior,
    make_derf_prior,
]


@pytest.fixture
def make_random_priors():
    def maker(count):
        return [fn() for fn in choices(MAKE_PRIOR, k=count)]

    return maker


def pytest_generate_tests(metafunc):
    """
    Parameterise prior mocking functions without requiring us to import MAKE_PRIOR
    """

    if "make_prior" in metafunc.fixturenames:
        metafunc.parametrize("make_prior", MAKE_PRIOR)
