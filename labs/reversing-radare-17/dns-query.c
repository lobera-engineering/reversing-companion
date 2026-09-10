#include <stdio.h>
#include <stdlib.h>
#include <winsock2.h>
#include <windows.h>
#include <conio.h>


#pragma comment(lib, "ws2_32")

#define BUFLEN 65536
int main(){

    char buffer[] = {
        0x00, 0x05, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x03, 0x77, 0x77, 0x77,
        0x02, 0x61, 0x62, 0x05, 0x6c, 0x6f, 0x63, 0x61,
        0x6c, 0x00, 0x00, 0x01, 0x00, 0x01 };

    char buf[BUFLEN];

    SOCKET sock;
    WSADATA wsa;
    SOCKADDR_IN ReceiverAddr , SrcInfo;
    SOCKADDR_IN SenderAddr;
    int slen = sizeof(ReceiverAddr) ;
    int port = 53;
    int bytes_rec=0;

	if (WSAStartup(MAKEWORD(2,2),&wsa) != 0){
		printf("Failed. Error Code : %d",WSAGetLastError());
		return 1;
	}

    if((sock = socket(AF_INET , SOCK_DGRAM, IPPROTO_UDP )) == INVALID_SOCKET){
        printf("Could not create socket : %d" , WSAGetLastError());
    }

    ReceiverAddr.sin_family = AF_INET;
    ReceiverAddr.sin_port = htons(port);
    ReceiverAddr.sin_addr.s_addr = inet_addr("192.168.0.50");

    if (sendto(sock, &buffer , sizeof(buffer) , 0, (struct SOCKADDR *) &ReceiverAddr, slen) == SOCKET_ERROR){
        printf("sendto() failed with error code : %d ", WSAGetLastError());
        exit(EXIT_FAILURE);
    }
    else{
        printf("packet sent\n");
    }

    bytes_rec=recvfrom(sock, &buf, BUFLEN, 0,0,0);
    if(bytes_rec > 0 ){
        printf("response: \n");
        for(int i = 0; i < bytes_rec; i++){
            printf("%x",buf[i]);
        }
        printf("\n");
        for(int i = 0; i < bytes_rec; i++){
            printf("%c",buf[i]);
        }
    }
    return 0;
}
