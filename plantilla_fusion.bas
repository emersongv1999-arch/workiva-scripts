Attribute VB_Name = "Modulo1"
' ============================================================================
' RESPALDO MANUAL -- ya no es el camino normal.
'
' LLENAR_XBRL.bat llama a "fusionar_cuadros.py --con-macros", que ahora hace
' exactamente esto mismo (Excel copiando hojas con Worksheets.Copy) pero
' manejado por Python via COM (pywin32), sin que haya que tocar nada a mano.
' Usa este modulo SOLO si ese paso del .bat avisa que no pudo armar el .xlsm
' (por ejemplo, en una maquina sin Excel instalado donde igual se quiere
' hacer la fusion despues, a mano, en otro computador que si tenga Excel).
'
' Por que este enfoque (Worksheets.Copy nativo) y no un .xlsm armado a mano
' ----------------------------------------------------------------------------
' El intento original de armar el .xlsm fusionado por fuera de Excel (pegando
' el vbaProject.bin de una plantilla donante en un paquete ZIP/XML hecho a
' mano) abre bien, se ve bien, pero el ActiveWorkbook.Save que hace la macro
' Copiar_columna revienta con error 1004 de forma consistente -- probado en
' OneDrive, en SharePoint y en un disco local sin ninguna nube de por medio.
' La causa exacta nunca se aislo del todo; lo unico que si se probo, una y
' otra vez, es que un archivo construido POR EXCEL MISMO no tiene ese
' problema. Por eso tanto este modulo como fusionar_cuadros.py --con-macros
' usan Worksheets.Copy en vez de ensamblar el paquete a mano.
'
' Como se usa (respaldo manual)
' ----------------------------------------------------------------------------
' 1. Alt+F11 -> clic derecho en el proyecto -> Importar archivo -> este .bas
'    (o abre este archivo como texto y pega su contenido en un modulo nuevo)
' 2. Guarda el libro que lo contiene como PLANTILLA_FUSION.xlsm en un lugar
'    fijo. Esa es tu plantilla reutilizable: no hay que repetir este paso.
' 3. Copia la carpeta salida\ completa (los .xlsm llenados por el .bat) a una
'    carpeta LOCAL, fuera de OneDrive/SharePoint (p.ej. C:\Temp\salida\).
'    Esto es obligatorio: Dir() no sabe leer rutas de SharePoint, y falla
'    con error 52 si se corre directo desde ahi.
' 4. Copia PLANTILLA_FUSION.xlsm dentro de esa misma carpeta local.
' 5. Abrela, Alt+F8 -> FusionarConMacro -> Ejecutar.
' 6. Ctrl+S. Listo: un solo archivo, con las hojas ya llenadas y las tres
'    macros funcionando de verdad.
' ============================================================================


Sub FusionarConMacro()
    Dim carpeta As String, archivo As String
    Dim libroOrigen As Workbook
    Dim hoja As Worksheet
    Dim nombresVistos As Object
    Dim s As Worksheet
    Dim total As Long, fallidos As String

    Set nombresVistos = CreateObject("Scripting.Dictionary")
    ' asi correrlo una segunda vez no duplica lo que ya se copio antes
    For Each s In ThisWorkbook.Worksheets
        nombresVistos(s.Name) = True
    Next s

    carpeta = ThisWorkbook.Path & "\"

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.AskToUpdateLinks = False

    archivo = Dir(carpeta & "*.xlsm")
    Do While archivo <> ""
        If carpeta & archivo <> ThisWorkbook.FullName And Left(archivo, 2) <> "~$" Then
            Set libroOrigen = Nothing
            On Error Resume Next
            Set libroOrigen = Workbooks.Open(carpeta & archivo, ReadOnly:=True, UpdateLinks:=False)
            On Error GoTo 0

            If libroOrigen Is Nothing Then
                fallidos = fallidos & "  - " & archivo & vbCrLf
            Else
                For Each hoja In libroOrigen.Worksheets
                    If EsHojaDeCuadro(hoja) And Not nombresVistos.exists(hoja.Name) Then
                        hoja.Copy After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count)
                        nombresVistos(hoja.Name) = True
                        total = total + 1
                    End If
                Next hoja
                libroOrigen.Close SaveChanges:=False
            End If
        End If
        archivo = Dir()
    Loop

    ' saca la hoja en blanco con la que arranca todo libro nuevo, si sigue vacia
    If ThisWorkbook.Sheets.Count > 1 And IsEmpty(ThisWorkbook.Sheets(1).Range("A1")) _
       And ThisWorkbook.Sheets(1).UsedRange.Address = "$A$1" Then
        ThisWorkbook.Sheets(1).Delete
    End If

    Application.DisplayAlerts = True
    Application.ScreenUpdating = True

    Dim msg As String
    msg = "Listo: " & total & " hojas nuevas copiadas." & vbCrLf & "Guarda con Ctrl+S."
    If fallidos <> "" Then
        msg = msg & vbCrLf & vbCrLf & "No se pudieron abrir:" & vbCrLf & fallidos
    End If
    MsgBox msg, vbInformation
End Sub


Private Function EsHojaDeCuadro(h As Worksheet) As Boolean
    ' Firma DBNeT: toda hoja de cuadro lleva URIs de taxonomia en la
    ' columna C. Las hojas auxiliares (codigo, Codigos, Hoja3) no.
    Dim c As Range
    For Each c In h.Range("C1:C500")
        If InStr(1, CStr(c.Value), ".xsd#") > 0 Then
            EsHojaDeCuadro = True
            Exit Function
        End If
    Next c
End Function


' ----------------------------------------------------------------------------
' Las tres macros originales de DBNeT, sin modificar. Van en el mismo modulo
' para que las hojas que se copien (con sus botones apuntando a "[0]!Nombre")
' encuentren el codigo dentro de ESTE libro.
' ----------------------------------------------------------------------------

Sub Guarda_Hojas_CSV()
    TotalHojas = ActiveWorkbook.Worksheets.Count
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    v_direc = Mid(ActiveWorkbook.Path, 1, Len(ActiveWorkbook.Path) - 3)
    For H = 1 To TotalHojas
        v_nombre = ActiveWorkbook.Worksheets(H).Name
        Sheets(H).Select
        Sheets(H).Copy
        ActiveWorkbook.SaveAs Filename:=v_direc & "csv\" & v_nombre & ".csv" _
            , FileFormat:=xlCSVWindows, CreateBackup:=False, Local:=True
        ActiveWorkbook.Close
    Next
End Sub


Sub Guarda_Hojas_ZIP()
    TotalHojas = ActiveWorkbook.Worksheets.Count
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    v_direc = Mid(ActiveWorkbook.Path, 1, Len(ActiveWorkbook.Path) - 3)
    For H = 1 To TotalHojas
        v_nombre = ActiveWorkbook.Worksheets(H).Name
        Sheets(H).Select
        Sheets(H).Copy
        ActiveWorkbook.SaveAs Filename:=v_direc & "csv\" & v_nombre & ".csv" _
            , FileFormat:=xlCSVWindows, CreateBackup:=False, Local:=True
        ActiveWorkbook.Close
    Next
    dRetVal = Shell(ActiveWorkbook.Path & "\zip.exe -jD " & ActiveWorkbook.Path & "\csv.zip " & v_direc & "csv\*.*", 0)
End Sub


Sub Copiar_columna()
    ActiveWorkbook.Save
    Dim MyColumn As String, Here As String, column As String, x As Integer
    Here = ActiveCell.Address
    x = ActiveCell.column
    If x > 6 Then
        MyColumn = Mid(Here, InStr(Here, "$") + 1, InStr(2, Here, "$") - 2)
        column = MyColumn & ":" & MyColumn
        Columns(column).Select
        Selection.Copy
        Selection.Insert Shift:=xlToRight
    End If
End Sub
