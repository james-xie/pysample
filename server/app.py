import optparse
import os
import sys
import zlib
import json
import logging
import datetime
import subprocess
from typing import Optional
from tempfile import NamedTemporaryFile

import flask_admin
from flask_admin import expose
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView
from flask import Flask, Response, request, jsonify, Blueprint, flash
from flask_admin.helpers import get_redirect_target
from flask_admin.model.filters import BaseFilter
from flask_admin.model.helpers import get_mdict_item_or_list
from sqlalchemy import UniqueConstraint, BigInteger, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, String, DateTime
from marshmallow import Schema, fields, validate
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import BadRequest
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import redirect

app = Flask("PySample")
errors = Blueprint("errors", __name__)
logger = logging.getLogger(__name__)

# example: mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4
if "DATABASE_URI" not in os.environ:
    raise ValueError("'DATABASE_URI' is not configured.")
else:
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URI"]

# example: /root/FlameGraph/flamegraph.pl
FLAMEGRAPH_PATH = os.environ.get("FLAMEGRAPH_PATH")

app.config["SECRET_KEY"] = "1234567890"
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class SampleRecord(db.Model):
    __tablename__ = "sample_records"

    id = Column(Integer, primary_key=True)
    project = Column(String(length=64), nullable=False)
    sample_id = Column(String(length=32), nullable=False)
    name = Column(String(length=255), nullable=False)
    process_id = Column(Integer, nullable=False)
    thread_id = Column(BigInteger, nullable=False)
    stack_info = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, nullable=False)
    execution_time = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("project", "sample_id", name="uk_project_sample_id"),
    )

    def __unicode__(self):
        return self.name


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

    error_type = error.__class__.__name__
    response = {"success": success, "error": {"type": error_type, "message": message}}
    logger.error(f"{error_type}: {str(error)}", exc_info=True)

    return jsonify(response), status_code


add_sample_schema = AddSampleInputSchema()


def timestamp_to_localtime(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


@app.route("/sample/add/<project>", methods=["POST"])
def add_sample(project: str):
    """
    Save the sampling result to database.

    This api entry is requested by pysample client usually.

    :param project:
    :return:
    """
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

    try:
        db.session.add(record)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
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
    record = (
        db.session.query(SampleRecord)
        .filter(SampleRecord.project == project, SampleRecord.sample_id == sample_id)
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
    """
    Show flame graph corresponding to project and sample_id.

    If the "FLAMEGRAPH_PATH" environment variable is not configured, an error is returned.

    :param project:
    :param sample_id:
    :return:
    """
    if not FLAMEGRAPH_PATH:
        return jsonify(
            success=False, error={"message": "'FLAMEGRAPH_PATH' is not configured."}
        )

    try:
        record = get_sample_record(project, sample_id)
    except NoResultFound:
        return jsonify(success=False, error={"message": "No result found"})

    with NamedTemporaryFile() as output_file:
        with NamedTemporaryFile() as input_file:
            input_file.write(record.stack_info.encode("utf8"))
            input_file.flush()

            cmd = f"{FLAMEGRAPH_PATH} {input_file.name} > {output_file.name}"
            try:
                retcode = subprocess.call(cmd, shell=True)
                if retcode < 0:
                    return jsonify(
                        success=False, error={"message": "Command execution failed"}
                    )
            except OSError as e:
                return jsonify(
                    success=False, error={"type": "OSError", "message": str(e)}
                )

        return Response(output_file.read())


class SimpleColumnFilter(BaseFilter):
    """
    Filter the column in the SampleRecord.
    """

    def __init__(
        self, name: str, options=None, data_type=None, key_name: Optional[str] = None
    ):
        super().__init__(name, options, data_type, key_name)

        self.column = getattr(SampleRecord, name)

    def operation(self):
        return gettext("equals")

    def apply(self, query, value):
        return query.filter(self.column == value)


class XPySampleIDFilter(BaseFilter):
    """
    Filter the X-PySampleID which obtained from response headers.

    X-PySampleID format:
        {project}/{sample_id}

    for example:
        web_project/50956e0070e1496e8d2486c6e79fc8f5
    """

    def __init__(self):
        super().__init__("X-PySample-ID")

        self.project = getattr(SampleRecord, "project")
        self.sample_id = getattr(SampleRecord, "sample_id")

    def operation(self):
        return gettext("equals")

    def apply(self, query, value):
        project, sample_id = value.split("/")
        return query.filter(self.project == project, self.sample_id == sample_id)

    def validate(self, value):
        if "/" in value:
            project, sample_id = value.split("/")
            if project and sample_id:
                return True
        return False


class SampleRecordView(ModelView):
    can_edit = False
    can_create = False
    can_delete = False
    can_view_details = True

    column_default_sort = ("id", True)

    column_list = (
        SampleRecord.id,
        SampleRecord.project,
        SampleRecord.sample_id,
        SampleRecord.name,
        SampleRecord.process_id,
        SampleRecord.thread_id,
        SampleRecord.execution_time,
        SampleRecord.created_at,
    )

    list_template = "list.html"

    column_filters = [XPySampleIDFilter(), SimpleColumnFilter("project")]

    @expose("/details/")
    def details_view(self):
        """
        Show flame graph when clicking the view details button.

        :return:
        """
        return_url = get_redirect_target() or self.get_url(".index_view")

        if not self.can_view_details:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, "id")
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            flash(gettext("Record does not exist."), "error")
            return redirect(return_url)

        return show_flame_graph(model.project, model.sample_id)


# Create admin with custom base template
admin = flask_admin.Admin(
    app, "PySampleList", base_template="layout.html", template_mode="bootstrap3"
)


admin.add_view(SampleRecordView(SampleRecord, db.session, url="/sample/"))


@app.route("/")
def index():
    return redirect("/sample/")


@app.route("/favicon.ico")
def favicon():
    return ""


def init():
    db.metadata.create_all(db.engine)


if __name__ == "__main__":
    usage = "%prog [-i init_db_tables] [-o host] [-p port]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-i",
        "--init",
        action="store_true",
        help="initialize database tables",
    )
    parser.add_option(
        "-o",
        "--host",
        default="127.0.0.1",
        help="the hostname to listen on",
    )
    parser.add_option(
        "-p",
        "--port",
        type=int,
        default=10002,
        help="the port of the webserver",
    )

    options, args = parser.parse_args()

    if options.init:
        init()
    else:
        app.run(host=options.host, port=options.port)
