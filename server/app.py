import os
import zlib
import json
import datetime
import subprocess
from tempfile import NamedTemporaryFile

from flask import Flask, Response, request, jsonify, Blueprint
from sqlalchemy import create_engine, UniqueConstraint, BigInteger, Text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from marshmallow import Schema, fields, validate
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import BadRequest


app = Flask("PySample")
errors = Blueprint("errors", __name__)

# example: mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4
if "DATABASE_URL" not in os.environ:
    raise ValueError("'DATABASE_URL' is not configured.")
else:
    SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]

# example: /root/FlameGraph/flamegraph.pl
FLAMEGRAPH_PATH = os.environ.get("FLAMEGRAPH_PATH")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
Base = declarative_base()


class SampleRecord(Base):
    __tablename__ = "sample_records"

    id = Column(Integer, primary_key=True)
    project = Column(String(length=64), nullable=False)
    sample_id = Column(String(length=32), nullable=False)
    name = Column(String(length=255), nullable=False)
    process_id = Column(Integer, nullable=False)
    thread_id = Column(BigInteger, nullable=False)
    stack_info = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    execution_time = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("project", "sample_id", name="uk_project_sample_id"),
    )


Base.metadata.create_all(engine)


class AddSampleInputSchema(Schema):
    sample_id = fields.Str(
        required=True,
        validate=validate.Length(min=32, max=32),
        description="sampling unique key in the project",
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        description="sampling name",
    )
    process_id = fields.Int(required=True)
    thread_id = fields.Int(required=True)
    timestamp = fields.Float(required=True)
    stack_info = fields.Str(required=True)
    execution_time = fields.Int(
        required=True, description="execution time in millisecond"
    )


@app.errorhandler(Exception)
def handle_error(error):
    message = [str(x) for x in error.args]
    status_code = 500
    success = False
    response = {
        "success": success,
        "error": {"type": error.__class__.__name__, "message": message},
    }

    return jsonify(response), status_code


Session = sessionmaker()
Session.configure(bind=engine)

add_sample_schema = AddSampleInputSchema()


def timestamp_to_localtime(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


@app.route("/sample/add/<project>", methods=["POST"])
def add_sample(project: str):
    req_data = request.data
    try:
        raw_data = zlib.decompress(req_data)
        data = json.loads(raw_data)
    except (TypeError, zlib.error, json.JSONDecodeError) as e:
        raise BadRequest(str(e))

    err = add_sample_schema.validate(data)
    if err:
        raise BadRequest(str(err))

    sample_id = data["sample_id"]
    created_at = timestamp_to_localtime(data["timestamp"])

    record = SampleRecord(
        project=project,
        sample_id=data["sample_id"],
        name=data["name"],
        process_id=data["process_id"],
        thread_id=data["thread_id"],
        created_at=created_at,
        stack_info=data["stack_info"],
        execution_time=data["execution_time"],
    )

    session = Session()

    try:
        session.add(record)
        session.commit()
    except IntegrityError:
        session.rollback()
        return jsonify(
            success=False,
            error={
                "type": "IntegrityError",
                "message": f"sample record '{project}/{sample_id}' already exists.",
            },
        )

    return jsonify(success=True)


def row2dict(row: SampleRecord):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)
    return d


def get_sample_record(project: str, sample_id: str) -> SampleRecord:
    session = Session()
    record = (
        session.query(SampleRecord)
        .filter(
            SampleRecord.project == project, SampleRecord.sample_id == sample_id
        )
        .one()
    )
    return record


@app.route("/sample/get/<project>/<sample_id>", methods=["GET"])
def sample_get(project: str, sample_id: str):
    try:
        record = get_sample_record(project, sample_id)
        return jsonify(success=True, data=row2dict(record))
    except NoResultFound:
        return jsonify(success=True, error={"message": "No result found"})


@app.route("/sample/flamegraph/<project>/<sample_id>", methods=["GET"])
def show_flame_graph(project: str, sample_id: str):
    if not FLAMEGRAPH_PATH:
        return jsonify(
            success=False,
            error={
                "message": "'FLAMEGRAPH_PATH' is not configured.",
            },
        )

    try:
        record = get_sample_record(project, sample_id)
    except NoResultFound:
        return jsonify(success=False, error={"message": "No result found"})

    with NamedTemporaryFile() as output_file:
        with NamedTemporaryFile() as input_file:
            input_file.write(record.stack_info.encode("utf8"))
            input_file.flush()

            cmd = f'{FLAMEGRAPH_PATH} {input_file.name} > {output_file.name}'
            try:
                retcode = subprocess.call(cmd, shell=True)
                if retcode < 0:
                    return jsonify(success=False, error={
                        "message": "Command execution failed"
                    })
            except OSError as e:
                return jsonify(success=False, error={
                    "type": "OSError",
                    "message": str(e)
                })

        return Response(output_file.read())


if __name__ == "__main__":
    app.run(port=11111)
