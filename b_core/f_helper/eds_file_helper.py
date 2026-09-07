"""EDS 파일 생성 헬퍼 — DeviceNet EDS 템플릿 치환 규칙의 소유자.

템플릿(RSRC_TEMPLATE_EDS_FILE)은 라인 지향 포맷이다:
- "Key =" 라인은 현재 param 값으로 재조립한다 (키 정확 일치 — ProdType 과
  ProdTypeStr 처럼 접두 관계인 키가 있으므로 부분 일치는 쓰지 않는다)
- Param 라인의 %1~%5 자리표시자는 데이터 타입(int16/real) 분기값으로 치환한다

필요한 param 값이 아직 없으면(None) ValueError 로 명확히 실패한다 —
연결/refresh 전에 생성하면 깨진 파일 대신 안내 메시지가 나가야 한다.
"""
import re
from datetime import datetime

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype.param_enum import (DeviceNetDataTypeEnum,
                                          DeviceNetDevTypeEnum,
                                          DeviceNetProfileTypeEnum)
from b_core.c_manager.parameter_manager import ParamManager

# "Name(2)/Name(4)" 형식 (Output/Input Name param 값)
_RE_NAME_LENGTH = re.compile(r"(.*?)\((\d+)\)")
# "Name [Length: 2]" 형식 (DeviceNetOut/InOldBitmap description)
_RE_BITMAP_LENGTH = re.compile(r"(.*?)\[Length:\s*(\d+)\]")
# 템플릿의 "Key =" 라인 (들여쓰기 보존용 그룹 포함)
_RE_KEY_LINE = re.compile(r"^(\s*)(\w+)\s*=")

# %1=CIP 타입코드, %2=바이트수, %3=min, %4=max, %5=소수 자릿수
_INT16_FIELDS = {"%1": "195", "%2": "2", "%3": "-32768",   "%4": "32767",   "%5": "0"}
_REAL_FIELDS  = {"%1": "202", "%2": "4", "%3": "-3.0E+38", "%4": "3.0E+38", "%5": "4"}

# 데이터 타입 분기(%1~%5)가 들어가는 Param 라인
_DATA_TYPE_PARAM_KEYS = {"Param3", "Param5", "Param8", "Param9", "Param10",
                         "Param11", "Param12", "Param13", "Param30"}

_OUTPUT_ASSEMBLY_NAME = "Output Assembly 1"
_OUTPUT_EPATH = "20 04 24 96 30 03"
_INPUT_ASSEMBLY_NAME = "Input Assembly 1"
_INPUT_EPATH = "20 04 24 64 30 03"

# 값이 None 이면 생성 자체가 불가능한 param 들 (이름 -> 전체 경로)
_REQUIRED_PARAM_PATHS = {
    "Vendor ID":        "Interface DeviceNet.Identity Object.Instance.Vendor ID (0x)",
    "Device Type":      "Interface DeviceNet.Identity Object.Instance.Device Type",
    "Product Code":     "Interface DeviceNet.Identity Object.Instance.Product Code (0x)",
    "Product Name":     "Interface DeviceNet.Identity Object.Instance.Product Name",
    "Revision":         "Interface DeviceNet.Identity Object.Instance.Revision (0x)",
    "Profile":          "Interface DeviceNet.Connection Object.Profile.Profile",
    "Data type":        "Interface DeviceNet.Connection Object.Profile.Data type",
    "Number of Valves": "Cluster.Settings.Number of Valves",
}

_OUTPUT_NAME_PATH    = "Interface DeviceNet.Connection Object.Output.Output Name"
_INPUT_NAME_PATH     = "Interface DeviceNet.Connection Object.Input.Input Name"
_OUTPUT_SEL_OLD_PATH = "Interface DeviceNet.Connection Object.Output.Output Selector Bitmap (old)"
_INPUT_SEL_OLD_PATH  = "Interface DeviceNet.Connection Object.Input.Input Selector Bitmap (old)"


def _parse_names(name_param) -> tuple[int, str]:
    """"Name(2)/Name(4)" 값 -> (총 바이트 길이, "Name(2),Name(4)"). 값 없음은 (0, "")."""
    total_length = 0
    names = []

    if name_param.value:
        for item in name_param.value.split("/"):
            match = _RE_NAME_LENGTH.search(item.strip())
            if match:
                length = int(match.group(2))
                total_length += length
                names.append(f"{match.group(1).strip()}({length})")

    return total_length, ",".join(names)


def _make_names(bitmap_param) -> tuple[int, str]:
    """selector bitmap 값 -> 켜진 비트들의 (총 바이트 길이, "Name(2),..").

    ref_list(DescriptionEnum)의 description 이 "Name [Length: N]" 형식이다.
    값 없음/enum 미지정은 (0, "")."""
    total_length = 0
    names = []
    bitmap = bitmap_param.value

    if bitmap and bitmap_param.ref_list is not None:
        for item in bitmap_param.ref_list:
            if (bitmap & (1 << item.value)) == 0:
                continue

            description = item.description.strip()
            match = _RE_BITMAP_LENGTH.search(description)
            if match:
                name = match.group(1).strip()
                length = int(match.group(2))
                total_length += length
                names.append(f"{name}({length})")
            else:
                names.append(description)

    return total_length, ",".join(names)


def create_eds_file(file_path: str) -> None:
    """템플릿을 현재 param 값으로 치환한 EDS 를 file_path 에 쓴다."""
    param_manager = ParamManager()

    values = {name: param_manager.get_by_full_path(path).value
              for name, path in _REQUIRED_PARAM_PATHS.items()}
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise ValueError(f"param not refreshed yet: {', '.join(missing)}")

    is_int16 = values["Data type"] == DeviceNetDataTypeEnum.INT16.value
    slave_count = values["Number of Valves"]

    if values["Profile"] == DeviceNetProfileTypeEnum.GENERIC_DEVICE_B.value:
        output_length, output_obj_names = _make_names(param_manager.get_by_full_path(_OUTPUT_SEL_OLD_PATH))
        input_length, input_obj_names = _make_names(param_manager.get_by_full_path(_INPUT_SEL_OLD_PATH))
    else:
        output_length, output_obj_names = _parse_names(param_manager.get_by_full_path(_OUTPUT_NAME_PATH))
        input_length, input_obj_names = _parse_names(param_manager.get_by_full_path(_INPUT_NAME_PATH))

    now = datetime.now()
    date_str = now.strftime("%m-%d-%Y")
    time_str = now.strftime("%H:%M:%S")

    key_values = {
        "CreateDate":  date_str,
        "CreateTime":  time_str,
        "ModDate":     date_str,
        "ModTime":     time_str,
        "VendCode":    str(values["Vendor ID"]),
        "ProdType":    str(values["Device Type"]),
        "ProdTypeStr": f'"{DeviceNetDevTypeEnum.get_desc(values["Device Type"])}"',
        "ProdCode":    str(values["Product Code"]),
        "MajRev":      str(values["Revision"] // 256),
        "MinRev":      str(values["Revision"] % 256),
        "ProdName":    f'"{values["Product Name"]}"',
        "Input1":      f'{input_length},0,0x000F,"{_INPUT_ASSEMBLY_NAME}",6,"{_INPUT_EPATH}","{input_obj_names}"',
        "Output1":     f'{output_length},0,0x000F,"{_OUTPUT_ASSEMBLY_NAME}",6,"{_OUTPUT_EPATH}","{output_obj_names}"',
    }

    with open(path_def.RSRC_TEMPLATE_EDS_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    fields = _INT16_FIELDS if is_int16 else _REAL_FIELDS
    lines = []

    for line in template.splitlines():
        match = _RE_KEY_LINE.match(line)
        key = match.group(2) if match else None

        if key in key_values:
            line = f"{match.group(1)}{key} = {key_values[key]};"
        elif key in _DATA_TYPE_PARAM_KEYS:
            for placeholder, value in fields.items():
                line = line.replace(placeholder, value)
        elif key == "Param16":
            if slave_count > 0:
                line = line.replace("%1", str(slave_count)).replace("%2", "Cluster information")
            else:
                line = line.replace("%1", "1").replace("%2", "Reserved")
        elif key == "Param28":
            # %3 은 소수 자릿수 (min/max 는 템플릿에 고정되어 있다)
            line = (line.replace("%1", fields["%1"])
                        .replace("%2", fields["%2"])
                        .replace("%3", fields["%5"]))

        lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
