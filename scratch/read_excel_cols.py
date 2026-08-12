import xlrd

def run():
    wb = xlrd.open_workbook("teste_teste_teste.xls")
    sheet = wb.sheet_by_index(0)
    
    headers = [sheet.cell_value(0, col) for col in range(sheet.ncols)]
    print(f"Headers: {headers}")
    
    for row_idx in range(1, sheet.nrows):
        row_vals = [sheet.cell_value(row_idx, col) for col in range(sheet.ncols)]
        row_dict = dict(zip(headers, row_vals))
        print(f"Row {row_idx}: {row_dict}")

if __name__ == "__main__":
    run()
