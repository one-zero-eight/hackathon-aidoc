from typing import Callable, Awaitable, Any, Optional
import os
import uuid
import json
from io import StringIO

import pandas as pd

from open_webui.apps.webui.models.chats import Chats
from open_webui.apps.webui.models.files import Files, FileForm
from open_webui.config import UPLOAD_DIR

from open_webui.utils.misc import add_or_update_system_message

VIZ_DIR = "visualizations"
INLET_SYSTEM_PROMPT = """
Если есть возможность визуализировать данные для улучшения понимания данных, сделай это следующим способом:
1. Сначала ответь на запрос пользователя.
2. Прочитай и изучи запрос:
• Пойми вопрос пользователя и определи предоставленные тобой данные. Если нет данных, которые нужно визуализировать, закончи свой ответ.
3. Проанализируй данные:
• Изучи данные в запросе, чтобы определить подходящий тип диаграммы (например, столбчатая диаграмма, круговая диаграмма, линейная диаграмма) для эффективной визуализации.
4. Сгенерируй HTML только если визуализация будет полезна для пользователя:
• Создай HTML-код для представления данных с использованием выбранного формата диаграммы.
5. Откалибруй шкалу диаграммы на основе данных:
• на основе данных постарайся сделать шкалу диаграммы максимально читаемой.

### Основные соображения:

- Сделай так, в данных удалились любые символы, кроме букв и цифр.
- HTML-код должен находиться в самом конце твоего ответа
- HTML-код должен быть в блоке ```html
- Используй только реальные данные, полученные из базы знаний
- Не смей обманывать пользователя

### Пример 1 : 
'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Chart</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div id="chart" style="width: 100%; height: 100vh;"></div>
    <button id="save-button">Save Screenshot</button>
    <script>
        // Data for the chart
        var data = [{
            x: [''Category 1'', ''Category 2'', ''Category 3''],
            y: [20, 14, 23],
            type: ''bar''
        }];

        // Layout for the chart
        var layout = {
            title: ''Interactive Bar Chart'',
            xaxis: {
                title: ''Categories''
            },
            yaxis: {
                title: ''Values''
            }
        };

        // Render the chart
        Plotly.newPlot(''chart'', data, layout);

        // Function to save screenshot
        document.getElementById(''save-button'').onclick = function() {
            Plotly.downloadImage(''chart'', {format: ''png'', width: 800, height: 600, filename: ''chart_screenshot''});
        };

        // Function to update chart attributes
        function updateChartAttributes(newData, newLayout) {
            Plotly.react(''chart'', newData, newLayout);
        }

        // Example of updating chart attributes
        var newData = [{
            x: [''Категория 1'', ''Категория 2'', ''Категория 3''],
            y: [10, 22, 30],
            type: ''bar''
        }];

        var newLayout = {
            title: ''Updated Bar Chart'',
            xaxis: {
                title: ''New Categories''
            },
            yaxis: {
                title: ''New Values''
            }
        };

        // Call updateChartAttributes with new data and layout
        // updateChartAttributes(newData, newLayout);
    </script>
</body>
</html>
'''

### Пример 2:
'''
<!DOCTYPE html>
<html>
<head>
    <title>Collaborateurs par Métier/Fonction</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div id="myChart" style="width: 100%; max-width: 700px; height: 500px; margin: 0 auto;"></div>
    <script>
        var data = [{
            x: ["Ingénieur Système", "Solution Analyst", "Ingénieur d''études et Développement", "Squad Leader", "Architecte d''Entreprise", "Tech Lead", "Architecte Technique", "Référent Méthodes / Outils"],
            y: [5, 3, 2, 1, 1, 1, 1, 1],
            type: "bar",
            marker: {
                color: "rgb(49,130,189)"
            }
        }];
        var layout = {
            title: "Collaborateurs de STT par Métier/Fonction",
            xaxis: {
                title: "Métier/Fonction"
            },
            yaxis: {
                title: "Nombre de Collaborateurs"
            }
        };
        Plotly.newPlot("myChart", data, layout);
    </script>
</body>
</html>
'''
"""

BAR_CHART_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="my-chart" style="width: 100%; height: 500px;"></div>
    <script>
        var data = [
            {
                x: {{x_values}},
                y: {{y_values}},
                type: 'bar'
            }
        ];

        var layout = {
            title: '{{title}}',
            xaxis: {
                title: '{{x_title}}'
            },
            yaxis: {
                title: '{{y_title}}'
            }
        };

        var charts = document.querySelectorAll('.my-chart');
        console.log(charts);
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

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __user__: Optional[dict] = None,
        __model__: Optional[dict] = None,
    ) -> dict:
        print("INLET body", json.dumps(body, ensure_ascii=False))
        if "messages" not in body:
            body["messages"] = []

        # add_or_update_system_message(INLET_SYSTEM_PROMPT, body["messages"])
        return body

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

        content_to_display = ""
        for file in files:
            csvs = file.meta.get("csvs", [])
            for csv in csvs:
                content_to_display += csv
                df = pd.read_csv(StringIO(csv))

                content = BAR_CHART_TEMPLATE

                content = content.replace("{{title}}", file.filename)
                content = content.replace(
                    "{{x_values}}", json.dumps(df.iloc[:, 0].tolist(), ensure_ascii=False)
                )
                content = content.replace(
                    "{{y_values}}", json.dumps(df.iloc[:, 1].tolist(), ensure_ascii=False)
                )
                content = content.replace("{{x_title}}", "X")
                content = content.replace("{{y_title}}", "Y")

                content_to_display += content
                content_to_display += "\n\n"

        html_file_id = self.write_content_to_file(
            content_to_display,
            __user__["id"],
            body["chat_id"],
            "html",
        )
        body["messages"][-1]["content"] += f"\n\n{{{{HTML_FILE_ID_{html_file_id}}}}}"

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
