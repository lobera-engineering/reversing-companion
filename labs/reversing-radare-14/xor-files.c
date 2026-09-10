#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#include <string.h>

#define MAX_DIR_LEN 260
#define BUF_SIZ 10
void cryp(char buf[]){

    char k[10] = "0123456789";

    for(int i = 0; i < sizeof(buf); i ++){
        buf[i] ^= k[i];
    }
}
void doFile(int hFile){
    char buf[BUF_SIZ];

    int totalBytesRead = 0;
    int dwBytesRead = 0;
    int fsize = GetFileSize(hFile, NULL);

    printf("File size in bytes: %d \n", fsize);

    printf("File content: \n");

    while(totalBytesRead < fsize){
        memset(buf,0,BUF_SIZ);
        ReadFile(hFile, buf, BUF_SIZ-1, &dwBytesRead, NULL);
        cryp(buf);
        LZSeek(hFile,-dwBytesRead,1);
        WriteFile(hFile, buf, dwBytesRead,NULL,NULL);
        printf("%s", buf);
        totalBytesRead += dwBytesRead;
    }
    printf("\n");
}

int main()
{
    printf("Hello world!\n");
    char base_path[MAX_DIR_LEN];

    WIN32_FIND_DATA FindFileData;
    HANDLE hFind;

    hFind = FindFirstFile("C:\\samples\\stor\\*.txt",&FindFileData);
    printf("Search handler = %d \n", hFind);

    do{
        memset(base_path,0,MAX_DIR_LEN);
        strcpy(base_path,"C:\\samples\\stor\\");

        strcat(base_path,FindFileData.cFileName);
        printf("Name= %s \n",base_path );

        int hFile = CreateFile(base_path,               // file to open
                       GENERIC_ALL,          // open for write
                       FILE_SHARE_WRITE | FILE_SHARE_READ,       // share for reading
                       NULL,                  // default security
                       OPEN_EXISTING,         // existing file only
                       FILE_ATTRIBUTE_NORMAL, // normal file
                       NULL);


        printf("File handle: %d \n", hFile);
        doFile(hFile);
    }
    while(FindNextFile(hFind, &FindFileData) != 0);
    return 0;
}
