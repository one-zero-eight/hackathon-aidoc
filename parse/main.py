import asyncio
from pathlib import Path
import bs4
from httpx import AsyncClient
from datetime import datetime
import pandas as pd
import re
import magic  # python-magic for file type detection

main_url = "https://www.disclosure.ru/issuer/7740000076/"

client = AsyncClient()

# Semaphore to limit the number of concurrent downloads
download_semaphore = asyncio.Semaphore(5)  # Set to desired concurrency limit


async def download_file(url, save_path):
    """Download the file from the given URL and save it to the specified path."""
    # Check if any file with the base name already exists
    existing_files = list(save_path.parent.glob(f"{save_path.stem}.*"))
    if existing_files:
        print(f"File already exists: {existing_files[0]}")
        return
    async with download_semaphore:  # Limit concurrency
        response = await client.get(url)
        if response.status_code == 200:
            # Detect file type and determine extension
            mime = magic.Magic(mime=True)
            content_type = mime.from_buffer(response.content)
            extension = content_type.split("/")[
                -1
            ]  # Get the extension based on MIME type

            # Append the extension to the save path
            save_path = save_path.with_suffix(f".{extension}")

            # Ensure the directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Save the file
            with save_path.open("wb") as f:
                f.write(response.content)
            print(f"Downloaded {save_path}")
        else:
            print(f"Failed to download {url} - Status code: {response.status_code}")


async def main():
    main_page_html_path = Path("main.html")
    if not main_page_html_path.exists():
        main_page = await client.get(main_url)
        main_page_html = main_page.content
        with main_page_html_path.open("wb") as f:
            f.write(main_page_html)
    with main_page_html_path.open("r") as f:
        main_page_html = f.read()
    soup = bs4.BeautifulSoup(main_page_html, "html.parser")

    # Dictionary to hold table data for each sheet
    tables_data = {}

    # Iterate over all tables in the parsed HTML
    for idx, table in enumerate(soup.find_all("table", class_="doctable")):
        # Find label above the table
        label = None
        previous_sibling = table.find_previous_sibling()
        while previous_sibling:
            if previous_sibling.name == "b":
                u_tag = previous_sibling.find("u")
                if u_tag:
                    label = u_tag.get_text(strip=True)
                    break
            previous_sibling = previous_sibling.find_previous_sibling()

        # Default to "Table {idx + 1}" if no label is found
        label = label or f"Table {idx + 1}"

        # Clean the label for sheet naming
        clean_label = re.sub(r"[:\/\\\?\*\[\]]", "", label)[:31]

        # Get the header from the first row
        first_row = table.find("tr")
        headers = []
        if first_row:
            headers = [
                header.get_text(strip=True) for header in first_row.find_all("th")
            ]
            if not headers:  # If no <th> headers, use <td> from the first row
                headers = [
                    cell.get_text(strip=True) for cell in first_row.find_all("td")
                ]

        # Identify "Дата" columns
        date_columns = [i for i, header in enumerate(headers) if "Дата" in header]

        # Collect rows of data
        rows_data = []
        download_tasks = []
        for row in table.find_all("tr")[1:]:  # Skip the header row
            cells = row.find_all(["td", "th"])
            row_data = []
            for i, cell in enumerate(cells):
                save_path = None
                # Check if the cell contains a link
                link = cell.find("a")
                if link and link.has_attr("href"):
                    cell_text = link["href"]
                    # Schedule the download if it's in the last column and has a URL
                    if i == len(cells) - 1:
                        second_column_value = (
                            cells[1].get_text(strip=True) if len(cells) > 1 else "file"
                        )
                        save_path = Path(
                            f"documents/{clean_label}/{second_column_value[:100]}"
                        )
                        download_tasks.append((cell_text, save_path))
                else:
                    cell_text = cell.get_text(strip=True)
                    # Parse as datetime if column is a "Дата" column
                    if i in date_columns:
                        try:
                            cell_text = datetime.strptime(cell_text, "%d.%m.%Y").date()
                        except ValueError:
                            pass  # Leave cell_text as is if parsing fails
                row_data.append(cell_text)
                if save_path:
                    row_data.append(save_path)
            rows_data.append(row_data)

        # Create a DataFrame for the table
        df = pd.DataFrame(rows_data, columns=headers + ["Path"])
        tables_data[clean_label] = (
            df  # Store the DataFrame with the cleaned label as the key
        )

        # Execute download tasks sequentially to respect semaphore limits
        for url, path in download_tasks:
            await download_file(url, path)

    # Write all tables to an Excel file with each sheet named after the cleaned label
    output_path = "tables_data.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        for label, df in tables_data.items():
            df.to_excel(writer, sheet_name=label, index=False)

    print(f"Data has been saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
