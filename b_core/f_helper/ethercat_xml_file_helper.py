"""EtherCAT ESI(XML) 파일 생성 헬퍼 — 템플릿 치환 규칙의 소유자.

템플릿(RSRC_TEMPLATE_ETHERCAT_XML_FILE)은 라인 지향으로 처리한다:
"<Name>...</Name>" 마커 라인을 만나면 바로 다음 라인의 %1 을 해당 Range
param 의 Data type(FLOAT -> "REAL", INT -> "DINT")으로 치환한다. 같은
이름이 PDO 정의마다 반복 등장하므로 모든 등장을 치환한다.

필요한 param 값이 아직 없으면(None) ValueError 로 명확히 실패한다 —
연결/refresh 전에 생성하면 깨진 파일 대신 안내 메시지가 나가야 한다.
"""
from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype.param_enum import EtherCATDataTypeEnum
from b_core.c_manager.parameter_manager import ParamManager

# XML 의 <Name> 마커 -> Data type param 전체 경로.
# 마커 이름과 param 폴더 이름이 일치하지 않는 항목이 있어(예: External
# digital pressure sensor 1 <-> External digital sensor1) 명시적으로 매핑한다
_XML_NAME_TO_DATATYPE_PARAM = {
    "<Name>Pressure</Name>"                               : "Interface EtherCAT.Range.Pressure.Data type",
    "<Name>Pressure sensor 1</Name>"                      : "Interface EtherCAT.Range.Pressure sensor 1.Data type",
    "<Name>Pressure sensor 2</Name>"                      : "Interface EtherCAT.Range.Pressure sensor 2.Data type",
    "<Name>Position</Name>"                               : "Interface EtherCAT.Range.Position.Data type",
    "<Name>Target position</Name>"                        : "Interface EtherCAT.Range.Target position.Data type",
    "<Name>Cluster valve position</Name>"                 : "Interface EtherCAT.Range.Cluster valve position.Data type",
    "<Name>Pressure setpoint</Name>"                      : "Interface EtherCAT.Range.Pressure setpoint.Data type",
    "<Name>Position setpoint</Name>"                      : "Interface EtherCAT.Range.Position setpoint.Data type",
    "<Name>Pressure alignment setpoint</Name>"            : "Interface EtherCAT.Range.Pressure alignment setpoint.Data type",
    "<Name>External digital pressure sensor 1</Name>"     : "Interface EtherCAT.Range.External digital sensor1.Data type",
    "<Name>External digital pressure sensor 2</Name>"     : "Interface EtherCAT.Range.External digital sensor2.Data type",
    "<Name>Cluster valve freeze position setpoint</Name>" : "Interface EtherCAT.Range.Cluster valve freeze position.Data type",
}


def create_xml_file(file_path: str) -> None:
    """템플릿을 현재 Data type param 값으로 치환한 ESI XML 을 file_path 에 쓴다."""
    param_manager = ParamManager()

    values = {marker: param_manager.get_by_full_path(path).value
              for marker, path in _XML_NAME_TO_DATATYPE_PARAM.items()}
    missing = [path.split(".")[-2]
               for (marker, path), value in zip(_XML_NAME_TO_DATATYPE_PARAM.items(), values.values())
               if value is None]
    if missing:
        raise ValueError(f"param not refreshed yet: {', '.join(missing)}")

    with open(path_def.RSRC_TEMPLATE_ETHERCAT_XML_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    contents = []
    pending_datatype = None  # 직전 라인이 마커였으면 이번 라인의 %1 치환값

    for line in lines:
        if pending_datatype is not None:
            line = line.replace("%1", pending_datatype)
            pending_datatype = None
        else:
            for marker, value in values.items():
                if marker in line:
                    pending_datatype = "REAL" if value == EtherCATDataTypeEnum.FLOAT.value else "DINT"
                    break

        contents.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(contents) + "\n")
