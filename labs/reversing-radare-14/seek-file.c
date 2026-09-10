#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
int main()
{
    printf("Hello world!\n");
    char message[10] = "secret msg";
    int hFile = CreateFile("C:\\samples\\cat.jpg",               // file to open
                       GENERIC_WRITE,          // open for write
                       FILE_SHARE_WRITE,       // share for reading
                       NULL,                  // default security
                       OPEN_EXISTING,         // existing file only
                       FILE_ATTRIBUTE_NORMAL, // normal file
                       NULL);


    LZSeek(hFile,0,2); //0 bytes from the end

    WriteFile(hFile, message, 10,NULL,NULL);
    CloseHandle(hFile);
    return 0;
}
