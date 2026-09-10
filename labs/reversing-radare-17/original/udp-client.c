#include <stdio.h>
#include <stdlib.h>
#include <winsock2.h>
#include <windows.h>
#include <conio.h>

#pragma comment(lib, "ws2_32")

#define BUFLEN 65536

int main()
{
    char buffer[] = {'h','e','l','l','o'};

    SOCKET sock;
    WSADATA wsa;
    SOCKADDR_IN ReceiverAddr , SrcInfo;
    SOCKADDR_IN SenderAddr;
    int slen = sizeof(ReceiverAddr);
    int port = 5353;
    int bytes_rec=0;

	WSAStartup(MAKEWORD(2,2),&wsa);
    sock = socket(AF_INET , SOCK_DGRAM, IPPROTO_UDP);

    ReceiverAddr.sin_family = AF_INET;
    ReceiverAddr.sin_port = htons(port);
    ReceiverAddr.sin_addr.s_addr = inet_addr("192.168.0.50");

    int r =sendto(sock, &buffer , sizeof(buffer) , 0, (struct SOCKADDR *) &ReceiverAddr, slen);
    printf("bytes sent: %d \n", r);

    memset(buffer,0,5);

    bytes_rec=recvfrom(sock, &buffer, sizeof(buffer), 0,0,0);

    printf("bytes rec: %d \n", bytes_rec);
    printf("response: %s", buffer);

    return 0;
}
