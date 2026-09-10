# include <stdio.h>

main(){
 func();
 getchar();     
}

func(){
    int num[5];       
    int sum;            
    num[0] = 200;      
    num[1] = 150;
    num[2] = 100;
    num[3] = -50;
    num[4] = 300;
    sum = num[0] +     num[1] + num[2] + num[3] + num[4];
    printf("SUM IS %d", sum);
}
