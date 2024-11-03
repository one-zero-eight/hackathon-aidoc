from typing import Callable, Awaitable, Any, Optional
import os
import uuid
import json
from io import StringIO

import pandas as pd

from open_webui.apps.webui.models.chats import Chats
from open_webui.apps.webui.models.files import Files, FileForm
from open_webui.apps.webui.models.users import Users
from open_webui.config import UPLOAD_DIR
from open_webui.main import generate_chat_completions

VIZ_DIR = "visualizations"
SYSTEM_PROMPT_1 = """
You are professional in financial analytics. You should help to build a Plotly chart or table based on the given data to help your intern. This plot should be very useful for financial analytic. Always fallback to table format if the chart is not so informative.
Be concise and output the one type of chart or table that will be the most informative for the given data. Don't generate the code. Respond only with 1 sentence.
"""
USER_PROMPT_1 = """
X = {{X_DATA}}

Determine the type of chart or table that will be the most informative for the given data.
"""
SYSTEM_PROMPT_2 = """
You are professional in financial analytics. You should generate a Plotly chart or table based on the given data to help your intern. This plot should be very useful for financial analytic. Always fallback to table format if the chart is not so informative.

Think that var X already exists in global scope and contains dataframe. You should write parameters for Plotly: data and layout.
Output just the content of script that defines 'layout' and 'data' variables.
The script should start with <script> tag and end with </script> tag.

Example 1:

Input:
X = {
 "Полное наименование": ["Николаев Вячеслав Константинович", "Евтушенков Феликс Владимирович"],
 "ОГРН юридического лица | ИНН физического лица": [null, null],
 "Основание, в силу которого лицо признается аффилированным": [
    "Лицо осуществляет полномочия единоличного исполнительного...", 
    "Лицо является членом Совета директоров акционерного общества."
 ],
 "Дата наступления основания": ["13.03.2021", "23.06.2021"],
 "Доля участия аффилированного лица в уставном капитале акционерного общества, %": [0.0058, null],
 "Доля находящихся в распоряжении аффилированного лица голосующих акций акционерного общества, %": [0.0058, null]
}

Output:
<script>
    var layout = {
        title: 'Состав аффилированных лиц',
    };

    var data = [{
        type: 'table',
        header: {
            values: Object.keys(X),
            align: "center",
            line: { width: 1, color: 'black' },
            fill: { color: 'grey' },
            font: { family: 'Arial', size: 12, color: 'white' },
        },
        cells: {
            values: Object.values(X),
            align: 'center',
            line: { color: 'black', width: 1 },
            font: { family: 'Arial', size: 11, color: ['black'] },
        },
    }];
</script>

Example 2:

Input:
X = {
 "N п/п": [1, 2],
 "Наименование показателя": ["Объем голосового трафика, млрд мин. (Россия + Беларусь*)", "Количество мобильных абонентов, млн. абонентов. (Россия + Беларусь*)"],
 "Методика расчета показателя": ["Суммарный объем всех голосовых соединений абонентов", "Группа определяет в качестве..."],
 "6 мес. 2023": [169.8, 86.0],
 "6 мес. 2024": [163.4, 87.3]
}

Output:
<script>
    var layout = {
        title: 'Основные операционные показатели',
        barmode: 'group',
    };

    var data = [{
        type: 'bar',
        name: '6 мес. 2023',
        x: X["Наименование показателя"],
        y: X["6 мес. 2023"],
    }, {
        type: 'bar',
        name: '6 мес. 2024',
        x: X["Наименование показателя"],
        y: X["6 мес. 2024"],
    }];
</script>

Example 3:

Input:
X = {
 "Наименование показателя": ["Нематериальные активы", "Основные средства"],
 "Пояснения": ["", ""],
 "На 30 сентября 2022 года": [22221793, 17590294],
 "На 31 декабря 2021 года": [19762415, 17934546],
 "На 31 декабря 2020 года": [19090789, 17539906]
}

Output:
<script>
    var layout = {
        title: 'Показатели',
    };

    var data = [{
        type: 'scatter',
        name: X["Наименование показателя"][0],
        x: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"],
        y: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"].map(v=>X[v][0]),
    }, {
        type: 'scatter',
        name: X["Наименование показателя"][1],
        x: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"],
        y: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"].map(v=>X[v][1]),
    }, {
        type: 'scatter',
        name: X["Наименование показателя"][2],
        x: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"],
        y: ["На 31 декабря 2020 года", "На 31 декабря 2021 года", "На 30 сентября 2022 года"].map(v=>X[v][2]),
    }];
</script>
"""
USER_PROMPT_2 = """
{{MESSAGE_FROM_PROMPT_1}}

X = {{X_DATA}}

Generate the table or chart according to the determined type.
"""

PLOTLY_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="my-chart" style="width: 100%; height: 500px;"></div>
    <script>
        var X = {{X_DATA}}

        {{SCRIPT}}

        var charts = document.querySelectorAll('.my-chart');
        if (charts.length !== 0) {
            Plotly.newPlot(charts[charts.length-1], data, layout);
        }
    </script>
</body>
</html>
"""


class Filter:
    def __init__(self):
        pass

    async def outlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __user__: Optional[dict] = None,
        __model__: Optional[dict] = None,
    ) -> dict:
        print("OUTLET body", json.dumps(body, ensure_ascii=False))
        if not (
            body.get("chat_id")
            and body.get("messages")
            and __user__
            and "id" in __user__
        ):
            return body

        chat = Chats.get_chat_by_id(body["chat_id"])
        if not (chat and chat.chat.get("messages")):
            return body

        last_message = chat.chat["messages"][-1]
        used_files = set()
        for citation in last_message.get("citations", []):
            for meta in citation.get("metadata", []):
                if meta.get("file_id"):
                    used_files.add(meta.get("file_id"))

        if not used_files:
            return body

        used_files = sorted(list(used_files))
        files = Files.get_files_by_ids(used_files)

        user = Users.get_user_by_id(__user__["id"])

        content_to_display = ""
        for file in files:
            csvs = json.loads(file.meta.get("csvs", "[]"))
            for csv in csvs:
                df = pd.read_csv(StringIO(csv))
                json_x = json.dumps(df.to_dict("list"), ensure_ascii=False, indent=1)

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Finding the best chart type...",
                            "done": False,
                        },
                    }
                )

                payload_1 = {
                    "model": body["model"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_1},
                        {
                            "role": "user",
                            "content": USER_PROMPT_1.replace("{{X_DATA}}", json_x),
                        },
                    ],
                    "stream": False,
                }
                response_1 = await generate_chat_completions(
                    form_data=payload_1, user=user, bypass_filter=True
                )
                print("RESPONSE1", response_1)
                message_from_prompt_1: str = response_1["choices"][0]["message"][
                    "content"
                ]

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Generating the chart...",
                            "done": False,
                        },
                    }
                )

                payload_2 = {
                    "model": body["model"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_2},
                        {
                            "role": "user",
                            "content": USER_PROMPT_2.replace(
                                "{{MESSAGE_FROM_PROMPT_1}}", message_from_prompt_1
                            ).replace("{{X_DATA}}", json_x),
                        },
                    ],
                    "stream": False,
                }
                response_2 = await generate_chat_completions(
                    form_data=payload_2, user=user, bypass_filter=True
                )
                print("RESPONSE2", response_2)
                js_code: str = response_2["choices"][0]["message"]["content"]

                # Remove everything before <script> tag and <script> tag itself
                if "<script>" in js_code:
                    js_code = js_code[js_code.find("<script>") :]
                    js_code = js_code.replace("<script>", "")
                # Remove everything after </script> tag and </script> tag itself
                if "</script>" in js_code:
                    js_code = js_code[: js_code.find("</script>")]
                    js_code = js_code.replace("</script>", "")

                # Generate html content
                html_content = PLOTLY_TEMPLATE.replace("{{X_DATA}}", json_x).replace(
                    "{{SCRIPT}}", js_code
                )

                content_to_display += html_content
                content_to_display += "\n\n"

        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Generating the file...",
                    "done": False,
                },
            }
        )
        html_file_id = self.write_content_to_file(
            content_to_display,
            __user__["id"],
            body["chat_id"],
            "html",
        )
        body["messages"][-1]["content"] += f"\n\n{{{{HTML_FILE_ID_{html_file_id}}}}}"

        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Done creating charts.",
                    "done": True,
                },
            }
        )
        return body

    def write_content_to_file(self, content, user_id, chat_id, content_type):
        filename = f"{content_type}_{uuid.uuid4()}.html"

        relative_path = os.path.join(VIZ_DIR, content_type, chat_id, filename)
        chat_dir = os.path.join(UPLOAD_DIR, relative_path)
        file_path = os.path.join(chat_dir, filename)

        os.makedirs(chat_dir, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

        file_item = Files.insert_new_file(
            user_id,
            FileForm(
                id=str(uuid.uuid4()),
                filename=relative_path,
                path=file_path,
                meta={
                    "name": filename,
                    "content_type": "text/html",
                    "size": len(content),
                },
            ),
        )
        return file_item.id
