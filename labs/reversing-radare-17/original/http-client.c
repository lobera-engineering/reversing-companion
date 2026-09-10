#include <stdio.h>
#include <stdlib.h>
#include <winsock2.h>
#include <windows.h>
#include <conio.h>

#pragma comment(lib, "ws2_32")

#define BUFLEN 65536
#define KSIZE 300
#define BSIZE 256


void getCommand(char buf[], char command[]){
    int i = 0;
    int kg = 0;
    int ki = 0;

    while(i < BSIZE && kg == 0){
        if(buf[i]== '<' && buf[i+1] == 'm' && buf[i+2] == '>' ){

            for(int j=i+3; j < KSIZE+i+2; j++){
                command[ki] = buf[j];
                ki = ki+1;
            }
            kg = 1;
        }
        i = i+1;
    }
}

int main()
{
    char request[] = "GET /sec.txt HTTP/1.1\r\nUser-Agent: nc/0.0.1\r\nHost: 127.0.0.1\r\nAccept: */*\r\n\r\n";
    char buff_rec[BUFLEN];
    char command[KSIZE];
    memset(&buff_rec,0,BUFLEN);
    SOCKET sock;
    WSADATA wsa;
    SOCKADDR_IN ReceiverAddr , SrcInfo;
    SOCKADDR_IN SenderAddr;
    int slen = sizeof(ReceiverAddr);
    int port = 80;
    int bytes_rec=0;
    int recv_size=0;

	WSAStartup(MAKEWORD(2,2),&wsa);
    sock = socket(AF_INET , SOCK_STREAM, IPPROTO_TCP);

    ReceiverAddr.sin_family = AF_INET;
    ReceiverAddr.sin_port = htons(port);
    ReceiverAddr.sin_addr.s_addr = inet_addr("192.168.0.50");

    if (connect(sock, (struct sockaddr *) &ReceiverAddr , sizeof(ReceiverAddr)) < 0){
		printf("error \n");
		return 1;
	}

    if( send(sock , &request , strlen(request) , 0) < 0)
	{
		printf("send error\n");
		return 1;
	}

	if((recv_size = recv(sock , buff_rec , BUFLEN , 0)) == SOCKET_ERROR)
	{
		printf("recv error\n");
	}
	else{
        printf("size: %d \n",recv_size);
        printf("response: %s \n", buff_rec);
        printf("-----------------\n");
        getCommand(buff_rec, command);
        printf("command: %s \n", command);
	}
    return 0;
}
