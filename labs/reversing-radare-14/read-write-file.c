#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

#define BUFFERSIZE 180

int main()
{
    printf("Reading %d bytes: \n", BUFFERSIZE);
    DWORD  dwBytesRead = 0;
    char   ReadBuffer[BUFFERSIZE] = {0};
    int err;
    int totalBytesRead = 0;
    int r = 0;
    int hFile = CreateFile("C:\\samples\\newfile.txt",               // file to open
                       GENERIC_READ,          // open for read
                       FILE_SHARE_READ,       // share for read
                       NULL,                  // default security
                       OPEN_EXISTING,         // existing file only
                       FILE_ATTRIBUTE_NORMAL, // normal file
                       NULL);

    int hFile2 = CreateFile("C:\\samples\\newfile2.txt",               // file to open
                       GENERIC_WRITE,          // open for write
                       FILE_SHARE_WRITE,       // share for reading
                       NULL,                  // default security
                       OPEN_EXISTING,         // existing file only
                       FILE_ATTRIBUTE_NORMAL, // normal file
                       NULL);

    if (hFile == INVALID_HANDLE_VALUE || hFile2 == INVALID_HANDLE_VALUE)
    {
        err = GetLastError();
        printf("Error reading file, error code:  %d \n", err);

    }

    else{
        int fsize = GetFileSize(hFile, NULL);

        printf("File size in bytes: %d \n", fsize);

        printf("File content: \n");

        while(totalBytesRead < fsize){

            ReadFile(hFile, ReadBuffer, BUFFERSIZE-1, &dwBytesRead, NULL);
            printf("%s", ReadBuffer);
            totalBytesRead += dwBytesRead;

            WriteFile(hFile2, ReadBuffer, dwBytesRead,NULL,NULL);

        }

    }
    CloseHandle(hFile);
    CloseHandle(hFile2);

    return 0;
}
