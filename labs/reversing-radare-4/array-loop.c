# include <stdio.h>

main(){
 func();
 getchar();     
}

func(){

int arr[100];
for (int i=0;i<100;i++){
        arr[i]=i;
}
for (int i=0;i<100;i++){
        printf("val %d",arr[i]);
}
}
