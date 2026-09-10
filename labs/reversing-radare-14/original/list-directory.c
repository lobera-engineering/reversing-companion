#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#include <string.h>
int main()
{
    printf("Hello world!\n");

    WIN32_FIND_DATA FindFileData;
    HANDLE hFind;


    char base_path[MAX_DIR_LEN] = "C:\\samples\\stor\\";
    hFind = FindFirstFile("C:\\samples\\stor\\*.txt",&FindFileData);

    do{
        memset(base_path,0,MAX_DIR_LEN);
        strcpy(base_path,"C:\\samples\\stor\\");

        strcat(base_path,FindFileData.cFileName);
        printf("Name= %s \n",base_path );

    }
    while(FindNextFile(hFind, &FindFileData) != 0);

    printf("exit");
    CloseHandle(hFind);
    return 0;
}
