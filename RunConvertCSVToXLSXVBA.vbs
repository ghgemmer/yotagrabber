Option Explicit

On Error Resume Next


Sub RunConvertCSVToXLSX() 

  Dim xl 
  Dim xlApp 
  Dim xlBook 
  'WScript.Echo "Starting RunConvertCSVToXLSX"
  Set xl = CreateObject("Excel.Application") 
  Set xlBook = xl.Workbooks.Open("C:\Users\GregG\Documents\GitHub\yotagrabber\ConvertCSVToXLSXVBA.xlsm", 0, True) 
  xl.Application.Run "ConvertCSVToXlsx"
  xl.Quit 
  Set xlBook = Nothing 
  Set xl = Nothing 

End Sub 

RunConvertCSVToXLSX
