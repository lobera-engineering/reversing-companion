#include <strings.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include<string.h>
#include <stdint.h>

const uint8_t b2[4] = {
  0x90, 0x90, 0x90, 0x90
};

void main(){
    
    int (*func)();
    func = (int (*)()) b2;
    (int)(*func)();
    
}
