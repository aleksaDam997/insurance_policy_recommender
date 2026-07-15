from html import escape


def validation_report_to_html(report: dict) -> str:
    is_valid = report.get("IS_VALID", False)
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    excess_columns = report.get("excess_columns", [])
    used_columns = report.get("used_columns", [])

    status_color = "#28a745" if is_valid else "#dc3545"
    status_text = "VALIDNO" if is_valid else "NEVALIDNO"

    html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <title>Schema Validation Report</title>

                <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #f5f5f5;
                }}

                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}

                .status {{
                    background: {status_color};
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    text-align: center;
                }}

                .summary {{
                    display: flex;
                    gap: 15px;
                }}

                .summary-box {{
                    flex: 1;
                    text-align: center;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                }}

                .summary-number {{
                    font-size: 28px;
                    font-weight: bold;
                }}

                .error {{
                    color: #dc3545;
                }}

                .warning {{
                    color: #ff9800;
                }}

                .fill-low {{
                    color: #dc3545;
                    font-weight: bold;
                }}

                .fill-mid {{
                    color: #ff9800;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th {{
                    background: #343a40;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }}

                td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}

                tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                </style>
                </head>
                <body>

                <div class="card status">
                    Schema Validation: {status_text}
                </div>

                <div class="card">
                    <h2>Sažetak</h2>

                    <div class="summary">
                        <div class="summary-box">
                            <div class="summary-number">{len(errors)}</div>
                            <div>Greške</div>
                        </div>

                        <div class="summary-box">
                            <div class="summary-number">{len(warnings)}</div>
                            <div>Upozorenja</div>
                        </div>

                        <div class="summary-box">
                            <div class="summary-number">{len(excess_columns)}</div>
                            <div>Višak kolona</div>
                        </div>

                        <div class="summary-box">
                            <div class="summary-number">{len(used_columns)}</div>
                            <div>Korištene kolone</div>
                        </div>
                    </div>
                </div>
                """

    # Errors
    html += """
                <div class="card">
                <h2>Greške</h2>
            """

    if errors:
        html += "<ul>"
        for err in errors:
            html += f"<li class='error'>{escape(str(err))}</li>"
        html += "</ul>"
    else:
        html += "<p>Nema grešaka.</p>"

    html += "</div>"

    # Warnings
    html += """
                <div class="card">
                <h2>Upozorenja</h2>
            """

    if warnings:
        html += "<ul>"
        for warning in warnings:
            html += f"<li class='warning'>{escape(str(warning))}</li>"
        html += "</ul>"
    else:
        html += "<p>Nema upozorenja.</p>"

    html += "</div>"

    # Excess columns
    html += """
                <div class="card">
                <h2>Kolone koje postoje u CSV-u a nisu u schema.yaml</h2>

                <table>
                <tr>
                <th>Kolona</th>
                </tr>
                """

    if excess_columns:
        for col in excess_columns:
            html += f"<tr><td>{escape(str(col))}</td></tr>"
    else:
        html += "<tr><td>Nema viška kolona.</td></tr>"

    html += """
                </table>
                </div>
                """

    # Used columns — sada su UsedColumnReport objekti, ne stringovi
    html += """
                <div class="card">
                <h2>Korištene kolone</h2>

                <table>
                <tr>
                <th>Tabela</th>
                <th>Kolona</th>
                <th>Fill rate</th>
                <th>Broj jedinstvenih vrijednosti</th>
                </tr>
                """

    if used_columns:
        # sortiramo po fill_rate rastuće da problematične kolone budu vidljive prve
        sorted_cols = sorted(used_columns, key=lambda c: c.fill_rate)
        for col in sorted_cols:
            fill_rate = col.fill_rate
            if fill_rate < 50:
                fill_class = "fill-low"
            elif fill_rate < 90:
                fill_class = "fill-mid"
            else:
                fill_class = ""

            html += (
                "<tr>"
                f"<td>{escape(str(col.table_name))}</td>"
                f"<td>{escape(str(col.column_name))}</td>"
                f"<td class='{fill_class}'>{fill_rate}%</td>"
                f"<td>{col.nunique}</td>"
                "</tr>"
            )
    else:
        html += "<tr><td colspan='4'>Nema korištenih kolona.</td></tr>"

    html += """
                </table>
                </div>

                </body>
                </html>
                """

    return html