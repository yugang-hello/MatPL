module calc_deepMD1_feature
    use mod_mpi

    IMPLICIT NONE
    INTEGER :: ierr

    integer,allocatable,dimension (:) :: iatom
    integer num_step, natom, i, j,natom7,m_neigh7
    integer num_step0,num_step1,natom0,max_neigh
    real*8 Etotp_ave,E_tolerance

    integer n2b_t,n3b1_t,n3b2_t,it
    integer n2b_type(100),n2bm

    real*8 Rc_M
    integer n3b1m,n3b2m,kkk,ii

    real*8,allocatable,dimension (:,:) :: feat_M7
    real*8,allocatable,dimension (:,:,:,:) :: dfeat_M7
    integer,allocatable,dimension (:,:) :: list_neigh_alltypeM7
    integer,allocatable,dimension (:) :: num_neigh_alltypeM7
    integer nfeat0M7

    integer m_neigh,num,itype1,itype2,itype
    integer iat1,max_neigh_M,num_M
    
    integer ntype,n2b,n3b1,n3b2,nfeat0m,nfeat0(100)
    integer ntype1,ntype2,k1,k2,k12,ii_f,iat,ixyz
    integer iat_type(100)
    real*8 Rc, Rc2,Rm
    real*8 alpha31,alpha32

    real*8 Rc_type(100), Rc2_type(100), Rm_type(100),weight_rterm(100)
    real*8 w_dummy
    integer M_type(100),M1,M2_type(100),M2

    contains
    subroutine load_model_type7()
    
        open(10,file="input/gen_deepMD1_feature.in",status="old",action="read")
        rewind(10)
        read(10,*) Rc_M,m_neigh
        m_neigh7 = m_neigh
        read(10,*) ntype
        do i=1,ntype
            read(10,*) iat_type(i)
            read(10,*) Rc_type(i),Rc2_type(i),Rm_type(i)
            read(10,*) M_type(i),weight_rterm(i)
            ! add M2 as parameter defined by user
            read(10,*) M2_type(i), w_dummy
            if(Rc_type(i).gt.Rc_M) then
                write(6,*) "Rc_type must be smaller than Rc_M, gen_3b_feature.in",i,Rc_type(i),Rc_M
                stop
            endif
        enddo
        read(10,*) E_tolerance
        close(10)

        ! wlj alter 
        ! M1 M2 both controls feature num 
        nfeat0m=0
        
        do itype=1,ntype
            M1 = M_type(itype) * ntype
            M2 = M2_type(itype) * ntype
            ! wlj altered 
            nfeat0(itype) = M1*M2
            !nfeat0(itype)=M1*(M1+1)/2
            if(nfeat0(itype).gt.nfeat0m) nfeat0m=nfeat0(itype)
        enddo

        write(6,*) "itype,nfeat0=",(nfeat0(itype),itype=1,ntype)
    !cccccccccccccccccccccccccccccccccccccccc
    
!cccccccccccccccccccccccccccccccccccccccccccccccccccc
!  FInish the initial grid treatment

    end subroutine load_model_type7
    
    subroutine set_image_info_type7(atom_type_list,is_reset,natom_tmp)
        integer(4),dimension(:),intent(in) :: atom_type_list(natom_tmp)
        logical,intent(in) :: is_reset
        integer,intent(in) :: natom_tmp
        
            natom=natom_tmp
            natom7=natom
            if(is_reset) then 
              if(allocated(iatom))then
              deallocate(iatom)
              endif
            allocate(iatom(natom))                   
            iatom(1:natom)=atom_type_list(1:natom)
           endif
        
    end subroutine set_image_info_type7

    subroutine gen_deepMD1_feature(AL,xatom)
        integer(4)  :: itype,i,j
        integer ii,jj,jjm,iat
    
        real(8), intent(in) :: AL(3,3)
        real(8),dimension(:,:),intent(in) :: xatom
    
        integer,allocatable,dimension (:,:,:) :: list_neigh,iat_neigh,iat_neigh_M
        integer,allocatable,dimension (:,:) :: num_neigh
        real*8,allocatable,dimension (:,:,:,:) :: dR_neigh
        integer,allocatable,dimension (:,:) :: map2neigh_alltypeM
        integer,allocatable,dimension (:,:) :: list_tmp
        integer,allocatable,dimension (:) :: nfeat_atom
        integer,allocatable,dimension (:) :: itype_atom
        integer,allocatable,dimension (:,:,:) :: map2neigh_M
        integer,allocatable,dimension (:,:,:) :: list_neigh_M
        integer,allocatable,dimension (:,:) :: num_neigh_M
        integer,allocatable,dimension (:,:) :: list_neigh_alltype
        integer,allocatable,dimension (:) :: num_neigh_alltype
        real*8 :: timestart, timefinish
        real*8,allocatable,dimension (:,:) :: feat
        real*8,allocatable,dimension (:,:,:,:) :: dfeat
        real*8 tt2,tt1,tt0,tt3,tt4,tt5,tt6
    !cccccccccccccccccccccccccccccccccccccccccccccccccccc
        if (allocated(dfeat_M7)) then
            deallocate(feat_M7)
            deallocate(dfeat_M7)
            deallocate(list_neigh_alltypeM7)
            deallocate(num_neigh_alltypeM7)
        endif
    
    ! the dimension of these array, should be changed to natom_n
    ! instead of natom. Each process only needs to know its own natom_n
    
        allocate(list_neigh(m_neigh,ntype,natom))
        allocate(map2neigh_M(m_neigh,ntype,natom)) ! from list_neigh(of this feature) to list_neigh_all (of Rc_M
        allocate(list_neigh_M(m_neigh,ntype,natom)) ! the neigh list of Rc_M
        allocate(num_neigh_M(ntype,natom))
        allocate(iat_neigh(m_neigh,ntype,natom))
        allocate(dR_neigh(3,m_neigh,ntype,natom))   ! d(neighbore)-d(center) in xyz
        allocate(num_neigh(ntype,natom))
        allocate(list_neigh_alltype(m_neigh,natom))
        allocate(num_neigh_alltype(natom))
    
        allocate(iat_neigh_M(m_neigh,ntype,natom))
        allocate(list_neigh_alltypeM7(m_neigh,natom))
        allocate(num_neigh_alltypeM7(natom))
        allocate(map2neigh_alltypeM(m_neigh,natom)) ! from list_neigh(of this feature) to list_neigh_all (of Rc_M
        allocate(list_tmp(m_neigh,ntype))
        allocate(itype_atom(natom))
        allocate(nfeat_atom(natom))
    
        allocate(feat(nfeat0m,natom_n))         ! each note, only know its own feat
        allocate(dfeat(nfeat0m,natom_n,m_neigh,3))  ! dfeat is the derivative from the neighboring dR, 
        allocate(feat_M7(nfeat0m,natom_n))
        allocate(dfeat_M7(nfeat0m,natom_n,m_neigh,3))
    
        feat = 0.d0
        dfeat = 0.d0
        feat_M7 = 0.d0
        dfeat_M7 = 0.d0
        
    !ccccccccccccccccccccccccccccccccccccccccccc
        itype_atom=0
        do i=1,natom
        do j=1,ntype
         if(iatom(i).eq.iat_type(j)) then
          itype_atom(i)=j
         endif
        enddo
          if(itype_atom(i).eq.0) then
          write(6,*) "this atom type didn't found", itype_atom(i)
          stop
          endif
         enddo
    !ccccccccccccccccccccccccccccccccccccccccccc
    !    call cpu_time(timestart)
         call find_neighbore(iatom,natom,xatom,AL,Rc_type,num_neigh,list_neigh, &
         dR_neigh,iat_neigh,ntype,iat_type,m_neigh,Rc_M,map2neigh_M,list_neigh_M, &
         num_neigh_M,iat_neigh_M,inode,nnodes)
    
    !    call cpu_time(timefinish)
    !    write(*,*) 'find_nei time: ', timefinish-timestart
    !ccccccccccccccccccccccccccccccccc
    !ccccccccccccccccccccccccccccccccc
    
          max_neigh=-1
          num_neigh_alltype=0
          max_neigh_M=-1
          num_neigh_alltypeM7=0
          list_neigh_alltypeM7=0
    
          do iat=1,natom
    
          if(mod(iat-1,nnodes).eq.inode-1) then
    
    
          list_neigh_alltype(1,iat)=iat
          list_neigh_alltypeM7(1,iat)=iat
    
    
          num_M=1
          do itype=1,ntype
          do j=1,num_neigh_M(itype,iat)
          num_M=num_M+1
          if(num_M.gt.m_neigh) then
          write(6,*) "total num_neigh.gt.m_neigh,stop",m_neigh
          stop
          endif
          list_neigh_alltypeM7(num_M,iat)=list_neigh_M(j,itype,iat)
          list_tmp(j,itype)=num_M
          enddo
          enddo
    
    
          num=1
          map2neigh_alltypeM(1,iat)=1
          do  itype=1,ntype
          do   j=1,num_neigh(itype,iat)
          num=num+1
          list_neigh_alltype(num,iat)=list_neigh(j,itype,iat)
          map2neigh_alltypeM(num,iat)=list_tmp(map2neigh_M(j,itype,iat),itype)
    ! map2neigh_M(j,itype,iat), maps the jth neigh in list_neigh(Rc) to jth' neigh in list_neigh_M(Rc_M) 
          enddo
          enddo
    
    !ccccccccccccccccccccccccccccccccccccccc
    
    
          num_neigh_alltype(iat)=num
          num_neigh_alltypeM7(iat)=num_M
          if(num.gt.max_neigh) max_neigh=num
          if(num_M.gt.max_neigh_M) max_neigh_M=num_M
    
          endif
    
          enddo  ! iat
    
    !cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
    ! This num_neigh_alltype(iat) include itself !
    !    dfeat=0.d0
    !    feat=0.d0
    
          call find_feature_deepMD1(natom,itype_atom,Rc_type,Rc2_type,Rm_type,weight_rterm,&
          num_neigh,list_neigh,dR_neigh,iat_neigh,ntype,M_type, M2_type, &
          feat,dfeat,nfeat0m,m_neigh,nfeat_atom)
    !cccccccccccccccccccccccccccccccccccccccccccccccccccc
    

        do iat1=1,natom_n
        do ii=1,nfeat0m
        feat_M7(ii,iat1)=feat(ii,iat1)   
        enddo
        enddo
    
        iat1=0
        do iat=1,natom
        if(mod(iat-1,nnodes).eq.inode-1) then
        iat1=iat1+1
        do jj=1,num_neigh_alltype(iat)
        jjm=map2neigh_alltypeM(jj,iat)
        do ii=1,nfeat0m
        dfeat_M7(ii,iat1,jjm,1)=dfeat(ii,iat1,jj,1)  ! this is the feature stored in neigh list of Rc_M
        dfeat_M7(ii,iat1,jjm,2)=dfeat(ii,iat1,jj,2)
        dfeat_M7(ii,iat1,jjm,3)=dfeat(ii,iat1,jj,3)
        enddo
        enddo
        endif
        enddo
    
        nfeat0M7=nfeat0m    ! the number of features for feature type 1
    
    
        deallocate(list_neigh)
        deallocate(iat_neigh)
        deallocate(dR_neigh)
        deallocate(num_neigh)
        ! deallocate(feat)
        ! deallocate(dfeat)
        deallocate(list_neigh_alltype)
        deallocate(num_neigh_alltype)
    
    
        deallocate(list_neigh_M)
        deallocate(num_neigh_M)
        deallocate(map2neigh_M)
        deallocate(iat_neigh_M)
        ! deallocate(list_neigh_alltypeM7)
        ! deallocate(num_neigh_alltypeM7)
        deallocate(map2neigh_alltypeM)
        deallocate(list_tmp)
        deallocate(itype_atom)
        deallocate(nfeat_atom)
        deallocate(feat)
        deallocate(dfeat)
    



    end subroutine gen_deepMD1_feature


end module calc_deepMD1_feature